"""Business logic for membership arrears (close on payment, queries)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.models.arrears import MembershipArrear
from app.models.subscriptions import Payment

_OPEN = "open"
_PAID = "paid"


async def mark_arrear_paid_from_payment(
    db: AsyncSession, payment: Payment, now: datetime
) -> None:
    """Set arrear to paid when payment succeeds (Moneta/YooKassa/manual)."""
    if not payment.arrear_id:
        return
    ar = await db.get(MembershipArrear, payment.arrear_id)
    if not ar or ar.status != _OPEN:
        return
    ar.status = _PAID
    ar.paid_at = now
    ar.payment_id = payment.id


async def list_open_arrears_for_user(
    db: AsyncSession, user_id: UUID
) -> list[MembershipArrear]:
    result = await db.execute(
        select(MembershipArrear)
        .where(
            and_(
                MembershipArrear.user_id == user_id,
                MembershipArrear.status == _OPEN,
            )
        )
        .order_by(MembershipArrear.year.asc())
    )
    return list(result.scalars().all())


async def user_has_open_arrears(db: AsyncSession, user_id: UUID) -> bool:
    result = await db.execute(
        select(func.count(MembershipArrear.id)).where(
            and_(
                MembershipArrear.user_id == user_id,
                MembershipArrear.status == _OPEN,
            )
        )
    )
    return (result.scalar() or 0) > 0


def arrears_block_enabled(settings_data: dict[str, Any]) -> bool:
    raw = settings_data.get("arrears_block_membership_features")
    if raw is True:
        return True
    if isinstance(raw, dict) and raw.get("enabled") is True:
        return True
    if isinstance(raw, str) and raw.lower() in ("true", "1", "yes"):
        return True
    return False


async def load_site_settings_dict(db: AsyncSession) -> dict[str, Any]:
    from app.models.site import SiteSetting

    rows = (await db.execute(select(SiteSetting))).scalars().all()
    return {s.key: s.value for s in rows}


def correlated_open_arrears_exist() -> ColumnElement:
    """Correlated EXISTS: this doctor profile's user has an open membership arrear."""
    from app.models.profiles import DoctorProfile

    return (
        select(MembershipArrear.id)
        .where(
            and_(
                MembershipArrear.user_id == DoctorProfile.user_id,
                MembershipArrear.status == _OPEN,
            )
        )
        .correlate(DoctorProfile)
        .exists()
    )
