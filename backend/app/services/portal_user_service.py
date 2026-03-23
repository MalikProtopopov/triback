"""Portal user management — list and detail for non-admin users."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundError
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Subscription
from app.models.users import Role, TelegramBinding, User, UserRoleAssignment
from app.schemas.doctor_admin import (
    PortalUserDetailResponse,
    PortalUserListItem,
)
from app.schemas.shared import (
    PaymentNested,
    SubscriptionNested,
    payment_to_nested,
    subscription_to_nested,
)


class PortalUserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _latest_subscription_nested(self, user_id: UUID) -> SubscriptionNested | None:
        result = await self.db.execute(
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub = result.scalar_one_or_none()
        return subscription_to_nested(sub)

    async def list_portal_users(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        admin_roles = {"admin", "manager", "accountant"}

        admin_subq = (
            select(UserRoleAssignment.user_id)
            .join(Role, UserRoleAssignment.role_id == Role.id)
            .where(Role.name.in_(list(admin_roles)))
            .subquery()
        )

        base = select(User).where(~User.id.in_(select(admin_subq)))
        count_q = select(func.count(User.id)).where(~User.id.in_(select(admin_subq)))

        if search and len(search) >= 2:
            pattern = f"%{search}%"
            base = base.where(User.email.ilike(pattern))
            count_q = count_q.where(User.email.ilike(pattern))

        total = (await self.db.execute(count_q)).scalar() or 0

        sort_col = User.created_at
        base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
        base = base.offset(offset).limit(limit)

        users = (await self.db.execute(base)).scalars().all()
        u_ids = [u.id for u in users]

        roles_map: dict[UUID | str, list[str]] = {}
        if u_ids:
            role_q = await self.db.execute(
                select(UserRoleAssignment.user_id, Role.name)
                .join(Role, UserRoleAssignment.role_id == Role.id)
                .where(UserRoleAssignment.user_id.in_(u_ids))
            )
            for uid, rname in role_q.all():
                roles_map.setdefault(uid, []).append(rname)

        dp_map: dict[UUID | str, DoctorProfile] = {}
        if u_ids:
            dp_q = await self.db.execute(
                select(DoctorProfile).where(DoctorProfile.user_id.in_(u_ids))
            )
            for doc_profile in dp_q.scalars().all():
                dp_map[doc_profile.user_id] = doc_profile

        sub_map: dict[UUID, SubscriptionNested] = {}
        doctor_user_ids = [uid for uid, roles in roles_map.items() if "doctor" in roles]
        if doctor_user_ids:
            sub_q = (
                select(Subscription)
                .options(joinedload(Subscription.plan))
                .where(Subscription.user_id.in_(doctor_user_ids))
                .order_by(Subscription.user_id, Subscription.created_at.desc())
            )
            for s in (await self.db.execute(sub_q)).unique().scalars().all():
                if s.user_id not in sub_map:
                    nested = subscription_to_nested(s)
                    if nested:
                        sub_map[s.user_id] = nested

        tg_map: dict[UUID, TelegramBinding] = {}
        if u_ids:
            tg_rows = (
                await self.db.execute(
                    select(TelegramBinding).where(TelegramBinding.user_id.in_(u_ids))
                )
            ).scalars().all()
            for tb in tg_rows:
                tg_map[tb.user_id] = tb

        role_display_map = {"doctor": "Врач", "user": "Пользователь"}
        items: list[PortalUserListItem] = []
        for u in users:
            user_roles = roles_map.get(u.id, [])
            display_role = next((r for r in user_roles if r in ("doctor", "user")), None)

            dp = dp_map.get(u.id)
            dp_id = dp.id if dp else None
            full_name = f"{dp.last_name} {dp.first_name}" if dp else None
            board_role = dp.board_role if dp else None

            tg = tg_map.get(u.id)
            items.append(
                PortalUserListItem(
                    id=u.id,
                    email=u.email,
                    full_name=full_name,
                    role=display_role,
                    role_display=role_display_map.get(display_role, "Без роли") if display_role else "Без роли",
                    doctor_profile_id=dp_id,
                    subscription=sub_map.get(u.id) if display_role == "doctor" else None,
                    telegram_linked=tg is not None,
                    tg_username=tg.tg_username if tg else None,
                    board_role=board_role,
                    created_at=u.created_at,
                )
            )

        return {"data": items, "total": total, "limit": limit, "offset": offset}

    async def get_portal_user(self, user_id: UUID) -> PortalUserDetailResponse:
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")

        role_result = await self.db.execute(
            select(Role.name)
            .join(UserRoleAssignment, Role.id == UserRoleAssignment.role_id)
            .where(UserRoleAssignment.user_id == user.id)
        )
        user_roles = list(role_result.scalars().all())
        display_role = next((r for r in user_roles if r in ("doctor", "user")), None)
        role_display_map = {"doctor": "Врач", "user": "Пользователь"}

        dp_id: UUID | None = None
        full_name: str | None = None
        dp_status: str | None = None
        board_role: str | None = None
        sub_info: SubscriptionNested | None = None
        payments_list: list[PaymentNested] = []

        if display_role == "doctor":
            dp_result = await self.db.execute(
                select(DoctorProfile).where(DoctorProfile.user_id == user.id)
            )
            dp = dp_result.scalar_one_or_none()
            if dp:
                dp_id = dp.id
                full_name = f"{dp.last_name} {dp.first_name}"
                dp_status = dp.status
                board_role = dp.board_role
                sub_info = await self._latest_subscription_nested(user.id)

        pay_result = await self.db.execute(
            select(Payment)
            .where(Payment.user_id == user.id)
            .order_by(Payment.created_at.desc())
            .limit(20)
        )
        for p in pay_result.scalars().all():
            payments_list.append(payment_to_nested(p))

        tg_binding = (
            await self.db.execute(
                select(TelegramBinding).where(TelegramBinding.user_id == user.id)
            )
        ).scalar_one_or_none()

        return PortalUserDetailResponse(
            id=user.id,
            email=user.email,
            full_name=full_name,
            role=display_role,
            role_display=role_display_map.get(display_role, "Без роли") if display_role else "Без роли",
            is_verified=user.email_verified_at is not None,
            onboarding_status=None,
            doctor_profile_id=dp_id,
            doctor_profile_status=dp_status,
            subscription=sub_info,
            payments=payments_list,
            telegram_linked=tg_binding is not None,
            tg_username=tg_binding.tg_username if tg_binding else None,
            board_role=board_role,
            created_at=user.created_at,
        )
