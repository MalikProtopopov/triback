"""SubscriptionService — facade for subscription and payment operations.

Core pay/status logic lives here; other operations are delegated to
focused sub-services.  The class API is preserved for backward-compatibility
with existing router imports.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from redis.asyncio import Redis
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.enums import PaymentStatus, ProductType, SubscriptionStatus
from app.core.exceptions import AppValidationError, NotFoundError
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Plan, Subscription
from app.schemas.payments import ManualPaymentRequest, ManualPaymentResponse, PaymentListResponse
from app.schemas.subscriptions import (
    CurrentSubscriptionNested,
    PayResponse,
    PlanNested,
    SubscriptionStatusResponse,
)
from app.services.payment_admin_service import PaymentAdminService
from app.services.payment_service import YooKassaClient
from app.services.payment_user_service import PaymentUserService
from app.services.payment_utils import LAPSE_THRESHOLD_DAYS, build_receipt
from app.services.payment_webhook_service import PaymentWebhookService

logger = structlog.get_logger(__name__)

# Re-export for backward-compat (event_registration_service imports this)
_build_receipt = build_receipt


class SubscriptionService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:  # type: ignore[type-arg]
        self.db = db
        self.redis = redis
        self.yookassa = YooKassaClient()
        self._webhook = PaymentWebhookService(db)
        self._admin = PaymentAdminService(db)
        self._user = PaymentUserService(db)

    # ── POST /subscriptions/pay ───────────────────────────────────

    async def pay(self, user_id: UUID, plan_id: UUID, idempotency_key: str) -> PayResponse:
        cache_key = f"idempotency:pay:{user_id}:{idempotency_key}"
        cached = await self.redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return PayResponse(**data)

        plan = await self.db.get(Plan, plan_id)
        if not plan or not plan.is_active:
            raise NotFoundError("Plan not found or inactive")

        dp_result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        dp = dp_result.scalar_one_or_none()
        if not dp:
            raise NotFoundError("Doctor profile not found")
        if not dp.has_medical_diploma:
            raise AppValidationError(
                "Оплата невозможна без диплома о высшем медицинском образовании"
            )

        product_type = await self._determine_product_type(user_id)

        sub = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.PENDING_PAYMENT,
            is_first_year=product_type == ProductType.ENTRY_FEE,
        )
        self.db.add(sub)
        await self.db.flush()

        payment = Payment(
            user_id=user_id,
            amount=plan.price,
            product_type=product_type,
            payment_provider="yookassa",
            status=PaymentStatus.PENDING,
            subscription_id=sub.id,
            idempotency_key=idempotency_key,
            description=f"{plan.name} — Ассоциация трихологов",
        )
        self.db.add(payment)
        await self.db.flush()

        return_url = f"{settings.YOOKASSA_RETURN_URL}?payment_id={payment.id}"

        from app.models.users import User

        user_row = await self.db.execute(select(User.email).where(User.id == user_id))
        user_email = user_row.scalar_one_or_none() or ""

        receipt = build_receipt(
            email=user_email,
            description=payment.description or plan.name,
            amount=Decimal(str(plan.price)),
        )

        yookassa_resp = await self.yookassa.create_payment(
            amount=Decimal(str(plan.price)),
            description=payment.description or "",
            metadata={
                "internal_payment_id": str(payment.id),
                "product_type": product_type,
                "user_id": str(user_id),
            },
            idempotency_key=idempotency_key,
            return_url=return_url,
            receipt=receipt,
        )

        payment.external_payment_id = yookassa_resp.get("id")
        confirmation = yookassa_resp.get("confirmation", {})
        payment.external_payment_url = confirmation.get("confirmation_url")

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = (
                await self.db.execute(
                    select(Payment).where(
                        Payment.user_id == user_id,
                        Payment.idempotency_key == idempotency_key,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                return PayResponse(
                    payment_id=existing.id,
                    payment_url=existing.external_payment_url or "",
                    amount=float(existing.amount),
                )
            raise

        resp = PayResponse(
            payment_id=payment.id,
            payment_url=payment.external_payment_url or "",
            amount=float(plan.price),
        )

        ttl = getattr(settings, "PAYMENT_IDEMPOTENCY_TTL", 86400)
        await self.redis.set(cache_key, resp.model_dump_json(), ex=ttl)

        return resp

    async def _determine_product_type(self, user_id: UUID) -> str:
        result = await self.db.execute(
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
            )
            .order_by(Subscription.ends_at.desc())
            .limit(1)
        )
        latest_sub = result.scalar_one_or_none()

        if not latest_sub or latest_sub.ends_at is None:
            has_entry = await self._has_paid_entry_fee(user_id)
            return ProductType.SUBSCRIPTION if has_entry else ProductType.ENTRY_FEE

        now = datetime.now(UTC)
        if latest_sub.ends_at.tzinfo is None:
            lapse = now.replace(tzinfo=None) - latest_sub.ends_at
        else:
            lapse = now - latest_sub.ends_at

        if lapse > timedelta(days=LAPSE_THRESHOLD_DAYS):
            return ProductType.ENTRY_FEE
        return ProductType.SUBSCRIPTION

    async def _has_paid_entry_fee(self, user_id: UUID) -> bool:
        result = await self.db.execute(
            select(func.count(Payment.id)).where(
                and_(
                    Payment.user_id == user_id,
                    Payment.product_type == ProductType.ENTRY_FEE,
                    Payment.status == PaymentStatus.SUCCEEDED,
                )
            )
        )
        return (result.scalar() or 0) > 0

    # ── GET /subscriptions/status ─────────────────────────────────

    async def get_status(self, user_id: UUID) -> SubscriptionStatusResponse:
        result = await self.db.execute(
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        has_entry = await self._has_paid_entry_fee(user_id)

        if not latest:
            return SubscriptionStatusResponse(
                has_subscription=False,
                has_paid_entry_fee=has_entry,
                can_renew=False,
                next_action="pay_entry_fee" if not has_entry else "pay_subscription",
            )

        now = datetime.now(UTC)
        current: CurrentSubscriptionNested | None = None
        can_renew = False
        next_action: str | None = None

        if latest.status == SubscriptionStatus.ACTIVE and latest.ends_at:
            days_remaining = max(0, (latest.ends_at - now).days) if latest.ends_at.tzinfo else max(0, (latest.ends_at - now.replace(tzinfo=None)).days)
            current = CurrentSubscriptionNested(
                id=latest.id,
                plan=PlanNested(code=latest.plan.code, name=latest.plan.name),
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
            next_action = "complete_payment"

        return SubscriptionStatusResponse(
            has_subscription=latest.status == SubscriptionStatus.ACTIVE,
            current_subscription=current,
            has_paid_entry_fee=has_entry,
            can_renew=can_renew,
            next_action=next_action,
        )

    # ── Delegated methods (preserve original API) ─────────────────

    async def handle_webhook(self, body: dict[str, Any], client_ip: str) -> None:
        return await self._webhook.handle_webhook(body, client_ip)

    async def list_user_payments(self, user_id: UUID, *, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        return await self._user.list_user_payments(user_id, limit=limit, offset=offset)

    async def get_user_receipt(self, user_id: UUID, payment_id: UUID) -> dict[str, Any]:
        return await self._user.get_user_receipt(user_id, payment_id)

    async def list_payments(self, **kwargs: Any) -> PaymentListResponse:
        return await self._admin.list_payments(**kwargs)

    async def create_manual_payment(self, admin_id: UUID, body: ManualPaymentRequest) -> ManualPaymentResponse:
        return await self._admin.create_manual_payment(admin_id, body)

    async def initiate_refund(self, payment_id: UUID, amount: float | None, reason: str) -> dict[str, Any]:
        return await self._admin.initiate_refund(payment_id, amount, reason)
