"""Authentication service — registration, login, tokens, password/email management."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError, ConflictError, NotFoundError, UnauthorizedError
from app.core.permissions import get_sidebar_sections_for_role
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_token,
    hash_password,
    verify_password,
)
from app.models.users import Role, User, UserRoleAssignment
from app.schemas.auth import CurrentUserResponse
from app.tasks.email_tasks import (
    send_email_change_confirmation,
    send_password_reset_email,
    send_verification_email,
)

VERIFY_EMAIL_TTL = 24 * 3600  # 24 hours
RESET_PWD_TTL = 3600  # 1 hour
REFRESH_TTL = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
EMAIL_CHANGE_TTL = 24 * 3600  # 24 hours

_ROLE_PRIORITY = ("admin", "manager", "accountant", "doctor", "user")


def _pick_role(role_names: list[str]) -> str:
    """Return the highest-priority role from a list.

    Priority: admin > manager > accountant > doctor > user.
    Ensures staff users always get their staff role in the JWT even if they
    also have a 'doctor' or 'user' role assigned by mistake.
    """
    for role in _ROLE_PRIORITY:
        if role in role_names:
            return role
    return "user"


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    # ------------------------------------------------------------------
    # Registration & email verification
    # ------------------------------------------------------------------

    async def register(self, email: str, password: str) -> User:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ConflictError("Email is already registered")

        user = User(
            email=email,
            password_hash=hash_password(password),
        )
        self.db.add(user)
        await self.db.flush()

        user_role = await self.db.execute(select(Role).where(Role.name == "user"))
        role = user_role.scalar_one_or_none()
        if role:
            assignment = UserRoleAssignment(user_id=user.id, role_id=role.id)
            self.db.add(assignment)

        await self.db.commit()
        await self.db.refresh(user)

        token = generate_token()
        await self.redis.set(f"email_verify:{token}", str(user.id), ex=VERIFY_EMAIL_TTL)
        await send_verification_email.kiq(email, token)

        return user

    async def verify_email(self, token: str) -> None:
        user_id = await self.redis.get(f"email_verify:{token}")
        if not user_id:
            raise NotFoundError("Invalid or expired verification token")

        await self.redis.delete(f"email_verify:{token}")

        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")

        user.email_verified_at = datetime.now(tz=UTC)
        await self.db.commit()

    async def resend_verification_email(self, email: str) -> None:
        """Resend verification email. Always returns without raising for security."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return
        if user.email_verified_at:
            return

        key = f"resend_verify:{email.lower()}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 600)
        if count > 3:
            raise AppError(
                429,
                "RATE_LIMITED",
                "Слишком много запросов. Попробуйте через 10 минут",
            )

        token = generate_token()
        await self.redis.set(f"email_verify:{token}", str(user.id), ex=VERIFY_EMAIL_TTL)
        await send_verification_email.kiq(email, token)

    # ------------------------------------------------------------------
    # Login / refresh / logout
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> dict[str, str]:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("Account is deactivated")

        role_result = await self.db.execute(
            select(Role)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(UserRoleAssignment.user_id == user.id)
        )
        role_names = [r.name for r in role_result.scalars().all()]
        role_name = _pick_role(role_names)

        jti = generate_token(16)
        access_token = create_access_token(user.id, role_name)
        refresh_token = create_refresh_token(user.id, jti)

        await self.redis.set(
            f"refresh:{user.id}:{jti}", "1", ex=REFRESH_TTL
        )

        user.last_login_at = datetime.now(tz=UTC)
        await self.db.commit()

        return {"access_token": access_token, "refresh_token": refresh_token, "role": role_name}

    async def refresh_tokens(self, refresh_jwt: str) -> dict[str, str]:
        payload = decode_token(refresh_jwt)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token")

        user_id = payload["sub"]
        old_jti = payload["jti"]

        stored = await self.redis.get(f"refresh:{user_id}:{old_jti}")
        if not stored:
            raise UnauthorizedError("Refresh token revoked or expired")

        await self.redis.delete(f"refresh:{user_id}:{old_jti}")

        user = await self.db.get(User, user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or deactivated")

        role_result = await self.db.execute(
            select(Role)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(UserRoleAssignment.user_id == user.id)
        )
        role_names = [r.name for r in role_result.scalars().all()]
        role_name = _pick_role(role_names)

        new_jti = generate_token(16)
        new_access = create_access_token(UUID(user_id), role_name)
        new_refresh = create_refresh_token(UUID(user_id), new_jti)

        await self.redis.set(
            f"refresh:{user_id}:{new_jti}", "1", ex=REFRESH_TTL
        )

        return {"access_token": new_access, "refresh_token": new_refresh, "role": role_name}

    async def logout(self, refresh_jwt: str) -> None:
        payload = decode_token(refresh_jwt)
        if payload and payload.get("type") == "refresh":
            user_id = payload["sub"]
            jti = payload["jti"]
            await self.redis.delete(f"refresh:{user_id}:{jti}")

    async def logout_all_sessions(self, user_id: UUID) -> None:
        """Revoke every refresh session for this user (logout everywhere)."""
        pattern = f"refresh:{user_id}:*"
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)

    # ------------------------------------------------------------------
    # Password recovery
    # ------------------------------------------------------------------

    async def forgot_password(self, email: str) -> None:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return  # never reveal whether email exists

        staff_roles = {"admin", "manager", "accountant"}
        staff_role_q = await self.db.execute(
            select(Role.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.user_id == user.id,
                Role.name.in_(list(staff_roles)),
            )
        )
        is_staff = staff_role_q.scalar_one_or_none() is not None

        token = generate_token()
        await self.redis.set(f"reset_pwd:{token}", str(user.id), ex=RESET_PWD_TTL)
        await send_password_reset_email.kiq(email, token, is_staff=is_staff)

    async def reset_password(self, token: str, new_password: str) -> None:
        user_id = await self.redis.get(f"reset_pwd:{token}")
        if not user_id:
            raise NotFoundError("Invalid or expired reset token")

        await self.redis.delete(f"reset_pwd:{token}")

        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")

        user.password_hash = hash_password(new_password)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Authenticated user actions
    # ------------------------------------------------------------------

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> None:
        user = await self.db.get(User, str(user_id))
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect")

        user.password_hash = hash_password(new_password)
        await self.db.commit()

    async def change_email(
        self, user_id: UUID, new_email: str, password: str
    ) -> None:
        user = await self.db.get(User, str(user_id))
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Password is incorrect")

        existing = await self.db.execute(select(User).where(User.email == new_email))
        if existing.scalar_one_or_none():
            raise ConflictError("Email is already in use")

        token = generate_token()
        payload = json.dumps({"user_id": str(user_id), "new_email": new_email})
        await self.redis.set(f"email_change:{token}", payload, ex=EMAIL_CHANGE_TTL)
        await send_email_change_confirmation.kiq(new_email, token)

    async def confirm_email_change(self, token: str) -> None:
        raw = await self.redis.get(f"email_change:{token}")
        if not raw:
            raise NotFoundError("Invalid or expired email change token")

        await self.redis.delete(f"email_change:{token}")

        data = json.loads(raw)
        user_id = data["user_id"]
        new_email = data["new_email"]

        existing = await self.db.execute(select(User).where(User.email == new_email))
        if existing.scalar_one_or_none():
            raise ConflictError("Email is already in use")

        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")

        user.email = new_email
        await self.db.commit()

    async def get_current_user_info(
        self, user_id: str, role: str
    ) -> CurrentUserResponse:
        """Return current user info with role and sidebar_sections for frontend."""
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")

        is_staff = role in ("admin", "manager", "accountant")
        sidebar_sections = get_sidebar_sections_for_role(role)

        return CurrentUserResponse(
            id=str(user.id),
            email=user.email,
            role=role,
            is_staff=is_staff,
            sidebar_sections=sidebar_sections,
        )
