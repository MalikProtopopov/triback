"""Shared DB helpers for subscription pay + status flows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import PaymentStatus, ProductType, SubscriptionStatus
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Subscription
from app.services.payment_utils import LAPSE_THRESHOLD_DAYS


async def is_entry_fee_exempt(db: AsyncSession, user_id: UUID) -> bool:
    row = await db.execute(
        select(DoctorProfile.entry_fee_exempt).where(DoctorProfile.user_id == user_id)
    )
    v = row.scalar_one_or_none()
    return bool(v)


async def determine_product_type(db: AsyncSession, user_id: UUID) -> str:
    if await is_entry_fee_exempt(db, user_id):
        return ProductType.SUBSCRIPTION

    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    latest_sub = result.scalar_one_or_none()

    has_entry = await has_paid_entry_fee(db, user_id)

    if not latest_sub or latest_sub.ends_at is None:
        return ProductType.SUBSCRIPTION if has_entry else ProductType.ENTRY_FEE

    now = datetime.now(UTC)
    if latest_sub.ends_at.tzinfo is None:
        lapse = now.replace(tzinfo=None) - latest_sub.ends_at
    else:
        lapse = now - latest_sub.ends_at

    if not has_entry or lapse > timedelta(days=LAPSE_THRESHOLD_DAYS):
        return ProductType.ENTRY_FEE
    return ProductType.SUBSCRIPTION


async def has_paid_entry_fee(db: AsyncSession, user_id: UUID) -> bool:
    result = await db.execute(
        select(func.count(Payment.id)).where(
            and_(
                Payment.user_id == user_id,
                Payment.product_type == ProductType.ENTRY_FEE,
                Payment.status == PaymentStatus.SUCCEEDED,
            )
        )
    )
    return (result.scalar() or 0) > 0


async def has_live_pending_payment(
    db: AsyncSession, subscription_id: UUID, now: datetime
) -> bool:
    fallback_cutoff = now - timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS)
    result = await db.execute(
        select(func.count(Payment.id)).where(
            and_(
                Payment.subscription_id == subscription_id,
                Payment.status == PaymentStatus.PENDING,
                or_(
                    and_(Payment.expires_at.isnot(None), Payment.expires_at >= now),
                    and_(
                        Payment.expires_at.is_(None),
                        Payment.created_at >= fallback_cutoff,
                    ),
                ),
            )
        )
    )
    return (result.scalar() or 0) > 0


async def expire_stale_payment_inline(
    db: AsyncSession, sub: Subscription, now: datetime
) -> None:
    fallback_cutoff = now - timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS)
    stale_result = await db.execute(
        select(Payment).where(
            and_(
                Payment.subscription_id == sub.id,
                Payment.status == PaymentStatus.PENDING,
            )
        )
    )
    for p in stale_result.scalars().all():
        is_stale = (
            (p.expires_at is not None and p.expires_at < now)
            or (p.expires_at is None and p.created_at < fallback_cutoff)
        )
        if is_stale:
            p.status = PaymentStatus.EXPIRED

    sub.status = SubscriptionStatus.CANCELLED
    await db.commit()
