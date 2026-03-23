"""Initiate subscription / entry-fee payments."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import httpx
import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import PaymentStatus, ProductType, SubscriptionStatus
from app.core.exceptions import AppValidationError, NotFoundError
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Plan, Subscription
from app.schemas.subscriptions import PayResponse
from app.services.payment_creation import create_payment_via_provider
from app.services.payment_providers import PaymentItem
from app.services.payment_providers.protocols import PaymentProviderProtocol
from app.services.subscriptions import subscription_helpers as sub_helpers

logger = structlog.get_logger(__name__)


class SubscriptionPayService:
    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        provider: PaymentProviderProtocol,
    ) -> None:
        self.db = db
        self.redis = redis
        self.provider = provider

    async def pay(
        self, user_id: UUID, plan_id: UUID, idempotency_key: str
    ) -> PayResponse:
        cache_key = f"idempotency:pay:{user_id}:{idempotency_key}"

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
                await self.redis.delete(cache_key)

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
                existing_pay.expires_at is not None
                and existing_pay.expires_at < now
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

        product_type = await sub_helpers.determine_product_type(self.db, user_id)

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

            total_amount = Decimal(str(entry_plan.price)) + Decimal(
                str(sub_plan.price)
            )
            items = [
                PaymentItem(name=entry_plan.name, price=Decimal(str(entry_plan.price))),
                PaymentItem(name=sub_plan.name, price=Decimal(str(sub_plan.price))),
            ]
            description = (
                f"{entry_plan.name} + {sub_plan.name} — Ассоциация трихологов"
            )
        else:
            total_amount = Decimal(str(sub_plan.price))
            items = [
                PaymentItem(name=sub_plan.name, price=Decimal(str(sub_plan.price)))
            ]
            description = f"{sub_plan.name} — Ассоциация трихологов"

        sub = Subscription(
            user_id=user_id,
            plan_id=sub_plan.id,
            status=SubscriptionStatus.PENDING_PAYMENT,
            is_first_year=product_type == ProductType.ENTRY_FEE,
        )
        self.db.add(sub)
        await self.db.flush()

        if existing_pay and existing_pay.status != PaymentStatus.PENDING:
            existing_pay.idempotency_key = None
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
            expires_at=datetime.now(UTC)
            + timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS),
        )
        self.db.add(payment)
        await self.db.flush()

        from app.models.users import User

        user_row = await self.db.execute(select(User.email).where(User.id == user_id))
        user_email = user_row.scalar_one_or_none() or ""

        try:
            await create_payment_via_provider(
                self.provider,
                payment,
                items=items,
                total_amount=total_amount,
                description=description,
                customer_email=user_email,
                idempotency_key=idempotency_key,
                metadata={"product_type": product_type, "user_id": str(user_id)},
            )
        except (ValueError, RuntimeError, httpx.HTTPError) as exc:
            logger.error(
                "payment_provider_error",
                error=str(exc),
                provider=settings.PAYMENT_PROVIDER,
            )
            await self.db.rollback()
            raise AppValidationError(
                f"Ошибка платёжной системы: {exc}",
                details={"provider": settings.PAYMENT_PROVIDER},
            ) from exc

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
