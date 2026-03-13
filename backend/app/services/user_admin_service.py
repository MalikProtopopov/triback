"""Service for managing staff users (admin, manager, accountant)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.pagination import PaginatedResponse
from app.core.security import hash_password
from app.models.users import Role, User, UserRoleAssignment
from app.schemas.users_admin import (
    AdminUserCreatedResponse,
    AdminUserDetailResponse,
    AdminUserListItem,
    _ROLE_DISPLAY,
)

logger = structlog.get_logger(__name__)

_STAFF_ROLES = {"admin", "manager", "accountant"}


class UserAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_staff_users(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        role: str | None = None,
        search: str | None = None,
    ) -> PaginatedResponse:
        staff_subq = (
            select(UserRoleAssignment.user_id)
            .join(Role, UserRoleAssignment.role_id == Role.id)
            .where(Role.name.in_(list(_STAFF_ROLES)))
        )
        if role and role in _STAFF_ROLES:
            staff_subq = staff_subq.where(Role.name == role)
        staff_subq = staff_subq.subquery()

        base = select(User).where(User.id.in_(select(staff_subq)))
        count_q = select(func.count(User.id)).where(User.id.in_(select(staff_subq)))

        if search and len(search) >= 2:
            pattern = f"%{search}%"
            base = base.where(User.email.ilike(pattern))
            count_q = count_q.where(User.email.ilike(pattern))

        total = (await self.db.execute(count_q)).scalar() or 0
        base = base.order_by(User.created_at.desc()).offset(offset).limit(limit)
        users = (await self.db.execute(base)).scalars().all()

        u_ids = [u.id for u in users]
        roles_map: dict[UUID, str] = {}
        if u_ids:
            role_q = await self.db.execute(
                select(UserRoleAssignment.user_id, Role.name)
                .join(Role, UserRoleAssignment.role_id == Role.id)
                .where(
                    UserRoleAssignment.user_id.in_(u_ids),
                    Role.name.in_(list(_STAFF_ROLES)),
                )
            )
            for uid, rname in role_q.all():
                roles_map[uid] = rname

        items = [
            AdminUserListItem(
                id=u.id,
                email=u.email,
                role=roles_map.get(u.id, ""),
                role_display=_ROLE_DISPLAY.get(roles_map.get(u.id, ""), ""),
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in users
        ]
        return PaginatedResponse(data=items, total=total, limit=limit, offset=offset)

    async def get_staff_user(self, user_id: UUID) -> AdminUserDetailResponse:
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("Staff user not found")

        role_q = await self.db.execute(
            select(Role.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                Role.name.in_(list(_STAFF_ROLES)),
            )
        )
        role_name = role_q.scalar_one_or_none()
        if not role_name:
            raise NotFoundError("User is not a staff member")

        return AdminUserDetailResponse(
            id=user.id,
            email=user.email,
            role=role_name,
            role_display=_ROLE_DISPLAY.get(role_name, ""),
            is_active=user.is_active,
            is_verified=user.email_verified_at is not None,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )

    async def create_staff_user(
        self, data: dict[str, Any]
    ) -> AdminUserCreatedResponse:
        role_obj = (
            await self.db.execute(select(Role).where(Role.name == data["role"]))
        ).scalar_one_or_none()
        if not role_obj:
            raise NotFoundError(f"Role '{data['role']}' not found in database")

        user = User(
            email=data["email"],
            password_hash=hash_password(data["password"]),
            is_active=True,
        )
        self.db.add(user)

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("User with this email already exists") from None

        assignment = UserRoleAssignment(user_id=user.id, role_id=role_obj.id)
        self.db.add(assignment)
        await self.db.commit()

        logger.info("staff_user_created", user_id=str(user.id), role=data["role"])
        return AdminUserCreatedResponse(
            id=user.id,
            email=user.email,
            role=data["role"],
            role_display=_ROLE_DISPLAY.get(data["role"], ""),
        )

    async def update_staff_user(
        self, user_id: UUID, data: dict[str, Any]
    ) -> AdminUserDetailResponse:
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("Staff user not found")

        role_q = await self.db.execute(
            select(Role.name, UserRoleAssignment.role_id)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                Role.name.in_(list(_STAFF_ROLES)),
            )
        )
        current = role_q.first()
        if not current:
            raise NotFoundError("User is not a staff member")

        if "email" in data and data["email"] is not None:
            user.email = data["email"]

        if "is_active" in data and data["is_active"] is not None:
            user.is_active = data["is_active"]

        new_role = data.get("role")
        if new_role and new_role != current[0]:
            new_role_obj = (
                await self.db.execute(select(Role).where(Role.name == new_role))
            ).scalar_one_or_none()
            if not new_role_obj:
                raise NotFoundError(f"Role '{new_role}' not found in database")

            await self.db.execute(
                UserRoleAssignment.__table__.delete().where(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.role_id == current[1],
                )
            )
            self.db.add(UserRoleAssignment(user_id=user_id, role_id=new_role_obj.id))

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("User with this email already exists") from None

        return await self.get_staff_user(user_id)

    async def delete_staff_user(
        self, user_id: UUID, current_admin_id: UUID
    ) -> None:
        if user_id == current_admin_id:
            raise ForbiddenError("Cannot delete yourself")

        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("Staff user not found")

        role_q = await self.db.execute(
            select(Role.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                Role.name.in_(list(_STAFF_ROLES)),
            )
        )
        if not role_q.scalar_one_or_none():
            raise NotFoundError("User is not a staff member")

        user.is_active = False
        user.is_deleted = True
        await self.db.commit()
        logger.info("staff_user_deleted", user_id=str(user_id))
