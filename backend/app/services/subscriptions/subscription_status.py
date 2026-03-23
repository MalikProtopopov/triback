"""Build GET /subscriptions/status response."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.enums import SubscriptionStatus
from app.models.subscriptions import Plan, Subscription
from app.schemas.subscriptions import (
    CurrentSubscriptionNested,
    PlanNested,
    SubscriptionStatusResponse,
)
from app.services.payment_utils import LAPSE_THRESHOLD_DAYS
from app.services.subscriptions import subscription_helpers as sub_helpers


class SubscriptionUserStatusService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_status(self, user_id: UUID) -> SubscriptionStatusResponse:
        result = await self.db.execute(
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        has_entry = await sub_helpers.has_paid_entry_fee(self.db, user_id)
        entry_fee_required = not has_entry

        if has_entry and latest and latest.ends_at:
            now = datetime.now(UTC)
            if latest.ends_at.tzinfo is None:
                lapse = now.replace(tzinfo=None) - latest.ends_at
            else:
                lapse = now - latest.ends_at
            if lapse > timedelta(days=LAPSE_THRESHOLD_DAYS):
                entry_fee_required = True

        entry_fee_plan = None
        if entry_fee_required:
            ef_result = await self.db.execute(
                select(Plan).where(
                    Plan.plan_type == "entry_fee", Plan.is_active.is_(True)
                ).limit(1)
            )
            ef = ef_result.scalar_one_or_none()
            if ef:
                entry_fee_plan = PlanNested(
                    id=ef.id,
                    code=ef.code,
                    name=ef.name,
                    plan_type=ef.plan_type,
                    price=float(ef.price),
                    duration_months=ef.duration_months,
                )

        plans_result = await self.db.execute(
            select(Plan)
            .where(Plan.plan_type == "subscription", Plan.is_active.is_(True))
            .order_by(Plan.sort_order)
        )
        available_plans = [
            PlanNested(
                id=p.id,
                code=p.code,
                name=p.name,
                plan_type=p.plan_type,
                price=float(p.price),
                duration_months=p.duration_months,
            )
            for p in plans_result.scalars().all()
        ]

        if not latest:
            return SubscriptionStatusResponse(
                has_subscription=False,
                has_paid_entry_fee=has_entry,
                can_renew=False,
                next_action=(
                    "pay_entry_fee_and_subscription"
                    if entry_fee_required
                    else "pay_subscription"
                ),
                entry_fee_required=entry_fee_required,
                entry_fee_plan=entry_fee_plan,
                available_plans=available_plans,
            )

        now = datetime.now(UTC)
        current: CurrentSubscriptionNested | None = None
        can_renew = False
        next_action: str | None = None

        if latest.status == SubscriptionStatus.ACTIVE and latest.ends_at:
            days_remaining = (
                max(0, (latest.ends_at - now).days)
                if latest.ends_at.tzinfo
                else max(
                    0,
                    (latest.ends_at - now.replace(tzinfo=None)).days,
                )
            )
            current = CurrentSubscriptionNested(
                id=latest.id,
                plan=PlanNested(
                    id=latest.plan.id,
                    code=latest.plan.code,
                    name=latest.plan.name,
                    plan_type=getattr(latest.plan, "plan_type", "subscription"),
                    price=float(latest.plan.price),
                    duration_months=latest.plan.duration_months,
                ),
                status=latest.status,
                starts_at=latest.starts_at,
                ends_at=latest.ends_at,
                days_remaining=days_remaining,
            )
            if days_remaining < 30:
                can_renew = True
        elif latest.status == SubscriptionStatus.EXPIRED:
            next_action = "renew"
        elif latest.status == SubscriptionStatus.PENDING_PAYMENT:
            has_live_pending = await sub_helpers.has_live_pending_payment(
                self.db, latest.id, now
            )
            if has_live_pending:
                next_action = "complete_payment"
            else:
                await sub_helpers.expire_stale_payment_inline(self.db, latest, now)
                next_action = (
                    "pay_entry_fee_and_subscription"
                    if entry_fee_required
                    else "pay_subscription"
                )
        elif latest.status == SubscriptionStatus.CANCELLED:
            next_action = (
                "pay_entry_fee_and_subscription"
                if entry_fee_required
                else "pay_subscription"
            )

        return SubscriptionStatusResponse(
            has_subscription=latest.status == SubscriptionStatus.ACTIVE,
            current_subscription=current,
            has_paid_entry_fee=has_entry,
            can_renew=can_renew,
            next_action=next_action,
            entry_fee_required=entry_fee_required,
            entry_fee_plan=entry_fee_plan,
            available_plans=available_plans,
        )
