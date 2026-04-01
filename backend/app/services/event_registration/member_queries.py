"""Read-only checks for member pricing."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DoctorStatus, SubscriptionStatus
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Subscription
from app.services.membership_arrears_service import (
    arrears_block_enabled,
    load_site_settings_dict,
    user_has_open_arrears,
)


async def is_association_member(db: AsyncSession, user_id: UUID) -> bool:
    """True only if user is an ACTIVE doctor with an active subscription.

    When the ``arrears_block_membership_features`` toggle is enabled,
    users with open arrears are treated as non-members (regular pricing).
    """
    dp = await db.execute(
        select(DoctorProfile.id).where(
            DoctorProfile.user_id == user_id,
            DoctorProfile.status == DoctorStatus.ACTIVE,
        ).limit(1)
    )
    if not dp.scalar_one_or_none():
        return False

    sub = await db.execute(
        select(Subscription.id).where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            or_(
                Subscription.ends_at.is_(None),
                Subscription.ends_at > func.now(),
            ),
        ).limit(1)
    )
    if sub.scalar_one_or_none() is None:
        return False

    settings_data = await load_site_settings_dict(db)
    if arrears_block_enabled(settings_data):
        if await user_has_open_arrears(db, user_id):
            return False

    return True
