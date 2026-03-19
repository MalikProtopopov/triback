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

import httpx
import structlog
from redis.asyncio import Redis
from sqlalchemy import and_, func, or_, select
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
from app.services.payment_providers import PaymentItem, get_provider
from app.services.payment_user_service import PaymentUserService
from app.services.payment_utils import LAPSE_THRESHOLD_DAYS
from app.services.payment_webhook_service import PaymentWebhookService

logger = structlog.get_logger(__name__)


class SubscriptionService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:  # type: ignore[type-arg]
        self.db = db
        self.redis = redis
        self.provider = get_provider()
        self._webhook = PaymentWebhookService(db)
        self._admin = PaymentAdminService(db)
        self._user = PaymentUserService(db)

    # ── POST /subscriptions/pay ───────────────────────────────────

    async def pay(self, user_id: UUID, plan_id: UUID, idempotency_key: str) -> PayResponse:
        cache_key = f"idempotency:pay:{user_id}:{idempotency_key}"

        # Проверяем кэш, но сначала убеждаемся что платёж ещё pending и не истёк
        cached = await self.redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            cached_payment_id = data.get("payment_id")
            if cached_payment_id:
                existing_result = await self.db.execute(
                    select(Payment).where(Payment.id == cached_payment_id)
                )
                existing_pay = existing_result.scalar_one_or_none()
                now = datetime.now(UTC)
                is_still_valid = (
                    existing_pay is not None
                    and existing_pay.status == PaymentStatus.PENDING
                    and (
                        existing_pay.expires_at is None
                        or existing_pay.expires_at > now
                    )
                )
                if is_still_valid:
                    return PayResponse(**data)
                # Кэш устарел — удаляем и создаём новый платёж
                await self.redis.delete(cache_key)

        # Idempotency: вернуть существующий только если он ещё pending и не истёк
        existing_result = await self.db.execute(
            select(Payment).where(
                Payment.user_id == user_id,
                Payment.idempotency_key == idempotency_key,
            )
        )
        existing_pay = existing_result.scalar_one_or_none()
        if existing_pay and existing_pay.status == PaymentStatus.PENDING:
            now = datetime.now(UTC)
            is_expired = (
                existing_pay.expires_at is not None and existing_pay.expires_at < now
            )
            if not is_expired:
                resp = PayResponse(
                    payment_id=existing_pay.id,
                    payment_url=existing_pay.external_payment_url or "",
                    amount=float(existing_pay.amount),
                    expires_at=existing_pay.expires_at,
                )
                ttl = getattr(settings, "PAYMENT_IDEMPOTENCY_TTL", 86400)
                await self.redis.set(cache_key, resp.model_dump_json(), ex=ttl)
                return resp

        sub_plan = await self.db.get(Plan, plan_id)
        if not sub_plan or not sub_plan.is_active:
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

        # Build payment items depending on product_type
        if product_type == ProductType.ENTRY_FEE:
            entry_result = await self.db.execute(
                select(Plan).where(
                    Plan.plan_type == "entry_fee",
                    Plan.is_active.is_(True),
                ).limit(1)
            )
            entry_plan = entry_result.scalar_one_or_none()
            if not entry_plan:
                raise AppValidationError("Вступительный взнос не настроен")

            total_amount = Decimal(str(entry_plan.price)) + Decimal(str(sub_plan.price))
            items = [
                PaymentItem(name=entry_plan.name, price=Decimal(str(entry_plan.price))),
                PaymentItem(name=sub_plan.name, price=Decimal(str(sub_plan.price))),
            ]
            description = f"{entry_plan.name} + {sub_plan.name} — Ассоциация трихологов"
        else:
            total_amount = Decimal(str(sub_plan.price))
            items = [PaymentItem(name=sub_plan.name, price=Decimal(str(sub_plan.price)))]
            description = f"{sub_plan.name} — Ассоциация трихологов"

        sub = Subscription(
            user_id=user_id,
            plan_id=sub_plan.id,
            status=SubscriptionStatus.PENDING_PAYMENT,
            is_first_year=product_type == ProductType.ENTRY_FEE,
        )
        self.db.add(sub)
        await self.db.flush()

        # Очистить старый idempotency_key если платёж уже не pending
        if existing_pay and existing_pay.status != PaymentStatus.PENDING:
            existing_pay.idempotency_key = None  # type: ignore[assignment]
            await self.db.flush()

        payment = Payment(
            user_id=user_id,
            amount=float(total_amount),
            product_type=product_type,
            payment_provider=settings.PAYMENT_PROVIDER,
            status=PaymentStatus.PENDING,
            subscription_id=sub.id,
            idempotency_key=idempotency_key,
            description=description,
            expires_at=datetime.now(UTC) + timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS),
        )
        self.db.add(payment)
        await self.db.flush()

        from app.models.users import User

        user_row = await self.db.execute(select(User.email).where(User.id == user_id))
        user_email = user_row.scalar_one_or_none() or ""

        if settings.PAYMENT_PROVIDER == "moneta":
            return_url = settings.MONETA_RETURN_URL or settings.MONETA_SUCCESS_URL
        else:
            return_url = settings.YOOKASSA_RETURN_URL
        try:
            result = await self.provider.create_payment(
                transaction_id=str(payment.id),
                items=items,
                total_amount=total_amount,
                description=description,
                customer_email=user_email,
                return_url=return_url,
                idempotency_key=idempotency_key,
                metadata={"product_type": product_type, "user_id": str(user_id)},
            )
        except (ValueError, RuntimeError, httpx.HTTPError) as exc:
            logger.error("payment_provider_error", error=str(exc), provider=settings.PAYMENT_PROVIDER)
            await self.db.rollback()
            raise AppValidationError(
                f"Ошибка платёжной системы: {exc}",
                details={"provider": settings.PAYMENT_PROVIDER},
            ) from exc

        payment.external_payment_id = result.external_id or None
        payment.external_payment_url = result.payment_url
        if settings.PAYMENT_PROVIDER == "moneta" and result.external_id:
            payment.moneta_operation_id = result.external_id

        await self.db.commit()

        resp = PayResponse(
            payment_id=payment.id,
            payment_url=payment.external_payment_url or "",
            amount=float(total_amount),
            expires_at=payment.expires_at,
        )

        ttl = getattr(settings, "PAYMENT_IDEMPOTENCY_TTL", 86400)
        await self.redis.set(cache_key, resp.model_dump_json(), ex=ttl)

        return resp

    async def _determine_product_type(self, user_id: UUID) -> str:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        latest_sub = result.scalar_one_or_none()

        has_entry = await self._has_paid_entry_fee(user_id)

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

    async def _has_live_pending_payment(self, subscription_id: UUID, now: datetime) -> bool:
        """Check if there is at least one pending payment with a valid (non-expired) link."""
        fallback_cutoff = now - timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS)
        result = await self.db.execute(
            select(func.count(Payment.id)).where(
                and_(
                    Payment.subscription_id == subscription_id,
                    Payment.status == PaymentStatus.PENDING,
                    or_(
                        and_(Payment.expires_at.isnot(None), Payment.expires_at >= now),
                        and_(Payment.expires_at.is_(None), Payment.created_at >= fallback_cutoff),
                    ),
                )
            )
        )
        return (result.scalar() or 0) > 0

    async def _expire_stale_payment_inline(self, sub: Subscription, now: datetime) -> None:
        """Lazy cleanup: expire stale pending payments and cancel the subscription."""
        fallback_cutoff = now - timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS)
        stale_result = await self.db.execute(
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
                p.status = PaymentStatus.EXPIRED  # type: ignore[assignment]

        sub.status = SubscriptionStatus.CANCELLED  # type: ignore[assignment]
        await self.db.commit()

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
        entry_fee_required = not has_entry

        # Determine if lapsed subscription also needs entry_fee
        if has_entry and latest and latest.ends_at:
            now = datetime.now(UTC)
            if latest.ends_at.tzinfo is None:
                lapse = now.replace(tzinfo=None) - latest.ends_at
            else:
                lapse = now - latest.ends_at
            if lapse > timedelta(days=LAPSE_THRESHOLD_DAYS):
                entry_fee_required = True

        # Fetch entry_fee plan
        entry_fee_plan = None
        if entry_fee_required:
            ef_result = await self.db.execute(
                select(Plan).where(Plan.plan_type == "entry_fee", Plan.is_active.is_(True)).limit(1)
            )
            ef = ef_result.scalar_one_or_none()
            if ef:
                entry_fee_plan = PlanNested(
                    id=ef.id, code=ef.code, name=ef.name,
                    plan_type=ef.plan_type, price=float(ef.price),
                    duration_months=ef.duration_months,
                )

        # Fetch subscription plans
        plans_result = await self.db.execute(
            select(Plan).where(
                Plan.plan_type == "subscription", Plan.is_active.is_(True)
            ).order_by(Plan.sort_order)
        )
        available_plans = [
            PlanNested(
                id=p.id, code=p.code, name=p.name,
                plan_type=p.plan_type, price=float(p.price),
                duration_months=p.duration_months,
            )
            for p in plans_result.scalars().all()
        ]

        if not latest:
            return SubscriptionStatusResponse(
                has_subscription=False,
                has_paid_entry_fee=has_entry,
                can_renew=False,
                next_action="pay_entry_fee_and_subscription" if entry_fee_required else "pay_subscription",
                entry_fee_required=entry_fee_required,
                entry_fee_plan=entry_fee_plan,
                available_plans=available_plans,
            )

        now = datetime.now(UTC)
        current: CurrentSubscriptionNested | None = None
        can_renew = False
        next_action: str | None = None

        if latest.status == SubscriptionStatus.ACTIVE and latest.ends_at:
            days_remaining = max(0, (latest.ends_at - now).days) if latest.ends_at.tzinfo else max(0, (latest.ends_at - now.replace(tzinfo=None)).days)
            current = CurrentSubscriptionNested(
                id=latest.id,
                plan=PlanNested(
                    id=latest.plan.id, code=latest.plan.code, name=latest.plan.name,
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
            has_live_pending = await self._has_live_pending_payment(latest.id, now)
            if has_live_pending:
                next_action = "complete_payment"
            else:
                await self._expire_stale_payment_inline(latest, now)
                next_action = (
                    "pay_entry_fee_and_subscription" if entry_fee_required
                    else "pay_subscription"
                )
        elif latest.status == SubscriptionStatus.CANCELLED:
            next_action = (
                "pay_entry_fee_and_subscription" if entry_fee_required
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

    async def cancel_payment(self, payment_id: UUID, reason: str) -> dict[str, Any]:
        return await self._admin.cancel_payment(payment_id, reason)

    # ── POST /subscriptions/payments/{id}/check-status ─────────────

    async def check_payment_status(self, user_id: UUID, payment_id: UUID) -> dict[str, Any]:
        """Poll Moneta API for the real operation status and update payment if paid.

        Fallback mechanism for when Pay URL webhooks are not delivered
        (common in Moneta demo/test environments).
        """
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found")
        if payment.user_id != user_id:
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Payment belongs to another user")

        if payment.status != PaymentStatus.PENDING:
            return {
                "payment_id": payment.id,
                "status": payment.status,
                "changed": False,
                "message": f"Платёж уже в статусе '{payment.status}'",
            }

        operation_id = payment.moneta_operation_id or payment.external_payment_id
        if not operation_id:
            return {
                "payment_id": payment.id,
                "status": payment.status,
                "changed": False,
                "message": "Нет operation_id для проверки в Moneta",
            }

        from app.services.payment_providers.moneta_client import MonetaPaymentProvider

        provider = MonetaPaymentProvider()
        try:
            op_info = await provider.get_operation_status(operation_id)
        except Exception as exc:
            logger.warning("moneta_check_status_error", error=str(exc), operation_id=operation_id)
            return {
                "payment_id": payment.id,
                "status": payment.status,
                "changed": False,
                "message": f"Ошибка запроса к Moneta: {exc}",
            }

        moneta_status = op_info.get("status", "unknown")
        attrs = op_info.get("attributes", {})
        has_children = str(attrs.get("haschildren", "0")) != "0"

        logger.info(
            "moneta_poll_status",
            payment_id=str(payment_id),
            operation_id=operation_id,
            moneta_status=moneta_status,
            has_children=has_children,
        )

        confirmed_statuses = {"SUCCEED", "TAKENIN_NOTSENT", "TAKENOUT"}
        if moneta_status in confirmed_statuses or has_children:
            payment.moneta_operation_id = operation_id
            svc = PaymentWebhookService(self.db)
            await svc.handle_moneta_payment_succeeded(payment)
            return {
                "payment_id": payment.id,
                "status": PaymentStatus.SUCCEEDED,
                "changed": True,
                "message": "Платёж подтверждён через Moneta API",
            }

        return {
            "payment_id": payment.id,
            "status": payment.status,
            "changed": False,
            "moneta_status": moneta_status,
            "message": f"Операция в Moneta: {moneta_status}. Ожидаем подтверждения.",
        }
