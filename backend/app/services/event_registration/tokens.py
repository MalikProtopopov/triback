"""JWT access + refresh for post-registration sessions (guest confirm)."""

from __future__ import annotations

from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.users import Role, UserRoleAssignment


async def issue_registration_tokens(
    db: AsyncSession, redis: Redis, user_id: UUID
) -> tuple[str, str]:
    """Generate JWT access + refresh tokens and store refresh in Redis."""
    from app.core.security import (
        create_access_token,
        create_refresh_token,
        generate_token,
    )

    role_result = await db.execute(
        select(Role)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(UserRoleAssignment.user_id == user_id)
    )
    role_names = [r.name for r in role_result.scalars().all()]
    priority = ("admin", "manager", "accountant", "doctor", "user")
    role_name = next((r for r in priority if r in role_names), "user")

    jti = generate_token(16)
    access_token = create_access_token(user_id, role_name)
    refresh_token = create_refresh_token(user_id, jti)

    refresh_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    await redis.set(f"refresh:{user_id}:{jti}", "1", ex=refresh_ttl)

    return access_token, refresh_token
