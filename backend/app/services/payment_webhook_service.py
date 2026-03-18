"""Payment webhook handler — process YooKassa callbacks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    DoctorStatus,
    EventRegistrationStatus,
    PaymentStatus,
    ProductType,
    SubscriptionStatus,
)
from app.core.exceptions import ForbiddenError
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Plan, Subscription
from app.services.payment_utils import is_ip_allowed
from app.tasks.email_tasks import (
    send_payment_failed_notification,
    send_payment_succeeded_notification,
)

logger = structlog.get_logger(__name__)


class PaymentWebhookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def handle_webhook(self, body: dict[str, Any], client_ip: str) -> None:
        if not is_ip_allowed(client_ip):
            raise ForbiddenError("IP not in YooKassa whitelist")

        event = body.get("event", "")
        obj = body.get("object", {})
        external_id = obj.get("id")

        if not external_id:
            logger.warning("webhook_missing_external_id", body=body)
            return

        result = await self.db.execute(
            select(Payment)
            .where(Payment.external_payment_id == external_id)
            .with_for_update()
        )
        payment = result.scalar_one_or_none()

        if not payment:
            metadata = obj.get("metadata", {})
            internal_id = metadata.get("internal_payment_id")
            if internal_id:
                result = await self.db.execute(
                    select(Payment)
                    .where(Payment.id == internal_id)
                    .with_for_update()
                )
                payment = result.scalar_one_or_none()

        if not payment:
            logger.warning("webhook_payment_not_found", external_id=external_id)
            return

        if event == "payment.succeeded":
            await self._handle_payment_succeeded(payment, obj)
        elif event == "payment.canceled":
            await self._handle_payment_canceled(payment)
        elif event == "refund.succeeded":
            await self._handle_refund_succeeded(payment)
        else:
            logger.info("webhook_unknown_event", event=event)

    async def _handle_payment_succeeded(
        self, payment: Payment, obj: dict[str, Any]
    ) -> None:
        if payment.status == PaymentStatus.SUCCEEDED:
            return

        from app.models.subscriptions import Receipt

        now = datetime.now(UTC)
        payment.status = PaymentStatus.SUCCEEDED  # type: ignore[assignment]
        payment.paid_at = now

        if payment.product_type in (ProductType.ENTRY_FEE, ProductType.SUBSCRIPTION):
            await self._activate_subscription(payment, now)
        elif payment.product_type == ProductType.EVENT:
            await self._confirm_event_registration(payment)

        receipt_reg = obj.get("receipt_registration") or obj.get("receipt")
        if receipt_reg:
            receipt = Receipt(
                payment_id=payment.id,
                receipt_type="payment",
                provider_receipt_id=receipt_reg.get("id") or receipt_reg.get("receipt_id"),
                receipt_url=receipt_reg.get("receipt_url"),
                fiscal_number=receipt_reg.get("fiscal_provider_id"),
                fiscal_document=receipt_reg.get("fiscal_document_number"),
                fiscal_sign=receipt_reg.get("fiscal_sign"),
                receipt_data=receipt_reg,
                amount=payment.amount,
                status=PaymentStatus.SUCCEEDED,
            )
            self.db.add(receipt)

        await self.db.commit()

        from app.models.users import User

        email_result = await self.db.execute(
            select(User.email).where(User.id == payment.user_id)
        )
        email = email_result.scalar_one_or_none()
        if email:
            receipt_url = receipt_reg.get("receipt_url") if receipt_reg else None
            await send_payment_succeeded_notification.kiq(
                email, float(payment.amount), payment.product_type, receipt_url
            )
            from app.tasks.telegram_tasks import notify_admin_payment_received

            await notify_admin_payment_received.kiq(
                email, float(payment.amount), payment.product_type
            )

    async def _activate_subscription(self, payment: Payment, now: datetime) -> None:
        if not payment.subscription_id:
            return

        sub = await self.db.get(Subscription, payment.subscription_id)
        if not sub:
            return

        plan = await self.db.get(Plan, sub.plan_id)
        duration_months = plan.duration_months if plan else 12

        if sub.status != SubscriptionStatus.ACTIVE:
            sub.status = SubscriptionStatus.ACTIVE  # type: ignore[assignment]

        prev_end = sub.ends_at
        if prev_end and prev_end > now:
            sub.starts_at = sub.starts_at or now
        else:
            sub.starts_at = now

        from dateutil.relativedelta import relativedelta

        sub.ends_at = (sub.starts_at or now) + relativedelta(months=duration_months)

        dp_result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == payment.user_id)
        )
        dp = dp_result.scalar_one_or_none()
        if dp and dp.status == DoctorStatus.APPROVED:
            dp.status = DoctorStatus.ACTIVE  # type: ignore[assignment]

    async def _confirm_event_registration(self, payment: Payment) -> None:
        if not payment.event_registration_id:
            return
        from app.models.events import EventRegistration

        reg = await self.db.get(EventRegistration, payment.event_registration_id)
        if reg and reg.status != EventRegistrationStatus.CONFIRMED:
            reg.status = EventRegistrationStatus.CONFIRMED  # type: ignore[assignment]

    async def _handle_payment_canceled(self, payment: Payment) -> None:
        if payment.status in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED):
            return
        payment.status = PaymentStatus.FAILED  # type: ignore[assignment]

        if payment.product_type == ProductType.EVENT and payment.event_registration_id:
            await self._cancel_event_registration(payment)

        await self.db.commit()

        from app.models.users import User

        email_result = await self.db.execute(
            select(User.email).where(User.id == payment.user_id)
        )
        email = email_result.scalar_one_or_none()
        if email:
            await send_payment_failed_notification.kiq(email)

    async def _cancel_event_registration(self, payment: Payment) -> None:
        from app.models.events import EventRegistration, EventTariff

        reg = await self.db.get(EventRegistration, payment.event_registration_id)
        if not reg:
            return
        if reg.status != EventRegistrationStatus.CANCELLED:
            reg.status = EventRegistrationStatus.CANCELLED  # type: ignore[assignment]
            tariff = await self.db.get(EventTariff, reg.event_tariff_id)
            if tariff and tariff.seats_taken > 0:
                tariff.seats_taken -= 1

    async def _handle_refund_succeeded(self, payment: Payment) -> None:
        if payment.status == PaymentStatus.REFUNDED:
            return
        payment.status = PaymentStatus.REFUNDED  # type: ignore[assignment]

        if payment.product_type == ProductType.EVENT and payment.event_registration_id:
            await self._cancel_event_registration(payment)

        await self.db.commit()
