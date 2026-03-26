"""Payment webhook handler — process YooKassa and Moneta callbacks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import (
    DoctorStatus,
    EventRegistrationStatus,
    PaymentStatus,
    ProductType,
    ReceiptStatus,
    SubscriptionStatus,
)
from app.core.exceptions import ForbiddenError
from app.core.logging_privacy import yookassa_webhook_body_summary
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Subscription
from app.services.payment_utils import is_ip_allowed
from app.tasks.email_tasks import (
    send_arrear_paid_notification,
    send_payment_failed_notification,
    send_payment_succeeded_notification,
)

logger = structlog.get_logger(__name__)

_MSK = ZoneInfo("Europe/Moscow")


def _end_of_calendar_year_msk(year: int) -> datetime:
    return datetime(year, 12, 31, 23, 59, 59, tzinfo=_MSK)


class PaymentWebhookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _yookassa_api_allows_succeeded(
        self, external_id: str, payment: Payment
    ) -> bool:
        """Confirm ``payment.succeeded`` via YooKassa API when credentials exist."""
        if str(payment.payment_provider) != "yookassa":
            return True
        if not settings.YOOKASSA_WEBHOOK_VERIFY_WITH_API:
            return True
        if not (settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY):
            logger.warning("yookassa_api_verify_skipped_no_credentials")
            return True
        from app.services.payment_providers.yookassa_client import YooKassaPaymentProvider

        try:
            yk = YooKassaPaymentProvider()
            data = await yk.get_payment(external_id)
        except Exception:
            logger.exception(
                "yookassa_api_verify_request_failed",
                external_id=external_id[:48],
            )
            raise
        if data.get("status") != "succeeded":
            logger.warning(
                "yookassa_api_status_mismatch",
                external_id=external_id[:48],
                api_status=str(data.get("status", ""))[:32],
            )
            return False
        return True

    async def handle_webhook(self, body: dict[str, Any], client_ip: str) -> None:
        # Trust model: YooKassa does not provide per-merchant HMAC secrets.
        # Authentication relies solely on IP allowlist (YOOKASSA_IP_WHITELIST).
        # See also: https://yookassa.ru/developers/using-api/webhooks#security
        if not is_ip_allowed(client_ip):
            raise ForbiddenError("IP not in YooKassa whitelist")

        event = body.get("event", "")
        obj = body.get("object", {})
        external_id = obj.get("id")

        if not external_id:
            logger.warning(
                "webhook_missing_external_id",
                body_summary=yookassa_webhook_body_summary(body),
            )
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

        # См. app.services.payment_webhook_routing.YOOKASSA_WEBHOOK_EVENTS_HANDLED
        if event == "payment.succeeded":
            if not await self._yookassa_api_allows_succeeded(str(external_id), payment):
                return
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
        receipt_obj = obj.get("receipt_registration") or obj.get("receipt")
        await self._apply_payment_succeeded(
            payment, receipt_obj=receipt_obj, send_user_telegram=True
        )

    async def _apply_payment_succeeded(
        self,
        payment: Payment,
        *,
        receipt_obj: dict[str, Any] | None = None,
        send_user_telegram: bool = True,
    ) -> None:
        """Unified success handler for both YooKassa and Moneta.

        Args:
            payment: the Payment row, already locked with FOR UPDATE.
            receipt_obj: optional provider receipt dict (YooKassa only).
            send_user_telegram: send ``notify_user_payment_succeeded`` Telegram
                notification (YooKassa path); Moneta omits this since it sends
                a receipt notification separately via the receipt webhook.
        """
        if payment.status == PaymentStatus.SUCCEEDED:
            return

        from app.models.subscriptions import Receipt

        now = datetime.now(UTC)
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = now

        arrear_year_for_email: int | None = None
        if payment.product_type == ProductType.MEMBERSHIP_ARREARS:
            from app.models.arrears import MembershipArrear
            from app.services.membership_arrears_service import (
                mark_arrear_paid_from_payment,
            )

            await mark_arrear_paid_from_payment(self.db, payment, now)
            if payment.arrear_id:
                ar = await self.db.get(MembershipArrear, payment.arrear_id)
                if ar:
                    arrear_year_for_email = ar.year
        elif payment.product_type in (ProductType.ENTRY_FEE, ProductType.SUBSCRIPTION):
            await self._activate_subscription(payment, now)
        elif payment.product_type == ProductType.EVENT:
            await self._confirm_event_registration(payment)

        if receipt_obj:
            receipt = Receipt(
                payment_id=payment.id,
                receipt_type="payment",
                provider_receipt_id=receipt_obj.get("id") or receipt_obj.get("receipt_id"),
                receipt_url=receipt_obj.get("receipt_url"),
                fiscal_number=receipt_obj.get("fiscal_provider_id"),
                fiscal_document=receipt_obj.get("fiscal_document_number"),
                fiscal_sign=receipt_obj.get("fiscal_sign"),
                receipt_data=receipt_obj,
                amount=payment.amount,
                status=ReceiptStatus.SUCCEEDED,
            )
            self.db.add(receipt)

        await self.db.commit()

        if payment.product_type in (ProductType.ENTRY_FEE, ProductType.SUBSCRIPTION):
            await self._trigger_certificate_generation(payment.user_id, now.year)

        from app.models.users import User

        email_result = await self.db.execute(
            select(User.email).where(User.id == payment.user_id)
        )
        email = email_result.scalar_one_or_none()
        receipt_url = receipt_obj.get("receipt_url") if receipt_obj else None
        if email:
            if payment.product_type == ProductType.MEMBERSHIP_ARREARS:
                await send_arrear_paid_notification.kiq(
                    email,
                    float(payment.amount),
                    arrear_year_for_email or 0,
                )
            elif payment.product_type == ProductType.EVENT:
                await self._send_event_email(payment, email, receipt_url)
            else:
                await send_payment_succeeded_notification.kiq(
                    email, float(payment.amount), payment.product_type, receipt_url
                )
            from app.tasks.telegram_tasks import notify_admin_payment_received

            await notify_admin_payment_received.kiq(
                str(payment.user_id),
                email,
                float(payment.amount),
                str(payment.product_type),
            )
            if send_user_telegram and payment.product_type != ProductType.MEMBERSHIP_ARREARS:
                from app.tasks.telegram_tasks import notify_user_payment_succeeded

                await notify_user_payment_succeeded.kiq(
                    str(payment.user_id), float(payment.amount), payment.product_type
                )

    async def _activate_subscription(self, payment: Payment, now: datetime) -> None:
        if not payment.subscription_id:
            return

        sub = await self.db.get(Subscription, payment.subscription_id)
        if not sub:
            return

        if sub.status != SubscriptionStatus.ACTIVE:
            sub.status = SubscriptionStatus.ACTIVE

        now_msk = now.astimezone(_MSK) if now.tzinfo else now.replace(tzinfo=UTC).astimezone(_MSK)

        prev_end = sub.ends_at
        if prev_end is not None:
            prev_cmp = prev_end if prev_end.tzinfo else prev_end.replace(tzinfo=UTC)
            prev_msk = prev_cmp.astimezone(_MSK)
        else:
            prev_msk = None

        if prev_msk and prev_msk > now_msk:
            sub.starts_at = sub.starts_at or now
            sub.ends_at = _end_of_calendar_year_msk(prev_msk.year + 1)
        else:
            sub.starts_at = now
            sub.ends_at = _end_of_calendar_year_msk(now_msk.year)

        dp_result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == payment.user_id)
        )
        dp = dp_result.scalar_one_or_none()
        if dp and dp.status == DoctorStatus.APPROVED:
            dp.status = DoctorStatus.ACTIVE

    async def _confirm_event_registration(self, payment: Payment) -> None:
        if not payment.event_registration_id:
            return
        from app.models.events import EventRegistration

        reg = await self.db.get(EventRegistration, payment.event_registration_id)
        if reg and reg.status != EventRegistrationStatus.CONFIRMED:
            reg.status = EventRegistrationStatus.CONFIRMED

    async def _handle_payment_canceled(self, payment: Payment) -> None:
        if payment.status in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.EXPIRED):
            return
        payment.status = PaymentStatus.FAILED

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
        from app.tasks.telegram_tasks import notify_user_payment_failed

        await notify_user_payment_failed.kiq(str(payment.user_id))

    async def _cancel_event_registration(self, payment: Payment) -> None:
        from app.models.events import EventRegistration, EventTariff

        reg = await self.db.get(EventRegistration, payment.event_registration_id)
        if not reg:
            return
        if reg.status != EventRegistrationStatus.CANCELLED:
            reg.status = EventRegistrationStatus.CANCELLED
            tariff = await self.db.get(EventTariff, reg.event_tariff_id)
            if tariff and tariff.seats_taken > 0:
                tariff.seats_taken -= 1

    async def _handle_refund_succeeded(self, payment: Payment) -> None:
        if payment.status == PaymentStatus.REFUNDED:
            return
        payment.status = PaymentStatus.REFUNDED

        if payment.product_type == ProductType.EVENT and payment.event_registration_id:
            await self._cancel_event_registration(payment)

        await self.db.commit()

    async def _send_event_email(
        self, payment: Payment, email: str, receipt_url: str | None
    ) -> None:
        """Send a detailed event ticket email after successful payment."""
        from app.models.events import Event, EventRegistration

        if not payment.event_registration_id:
            await send_payment_succeeded_notification.kiq(
                email, float(payment.amount), payment.product_type, receipt_url
            )
            return

        reg = await self.db.get(EventRegistration, payment.event_registration_id)
        if not reg:
            await send_payment_succeeded_notification.kiq(
                email, float(payment.amount), payment.product_type, receipt_url
            )
            return

        event = await self.db.get(Event, reg.event_id)
        if not event:
            await send_payment_succeeded_notification.kiq(
                email, float(payment.amount), payment.product_type, receipt_url
            )
            return

        from app.tasks.email_tasks import send_event_ticket_purchased

        await send_event_ticket_purchased.kiq(
            email,
            event.title,
            event.event_date.strftime("%d.%m.%Y %H:%M") if event.event_date else "",
            event.event_end_date.strftime("%d.%m.%Y %H:%M") if event.event_end_date else None,
            event.location,
            float(reg.applied_price),
            reg.is_member_price,
            receipt_url,
        )
        from app.tasks.telegram_tasks import notify_user_event_ticket

        await notify_user_event_ticket.kiq(
            str(payment.user_id),
            event.title,
            event.event_date.strftime("%d.%m.%Y %H:%M") if event.event_date else "",
            float(reg.applied_price),
        )

    # ------------------------------------------------------------------
    # Moneta-specific handlers
    # ------------------------------------------------------------------

    async def _trigger_certificate_generation(self, user_id: Any, year: int) -> None:
        """Dispatch certificate generation if the user is an active doctor."""
        dp_result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        dp = dp_result.scalar_one_or_none()
        if dp and dp.status == DoctorStatus.ACTIVE:
            from app.tasks.certificate_tasks import generate_member_certificate_task

            await generate_member_certificate_task.kiq(str(dp.id), year)
            logger.info(
                "certificate_generation_triggered",
                doctor_profile_id=str(dp.id),
                year=year,
            )

    async def handle_moneta_payment_succeeded(self, payment: Payment) -> None:
        """Process a successful Moneta payment — delegates to the unified success handler.

        Moneta does not provide a receipt object at this stage (receipt URL arrives
        via the separate ``/webhooks/moneta/receipt`` callback), so ``receipt_obj``
        is omitted.  User Telegram notification is also omitted because Moneta sends
        its own receipt notification through the receipt webhook flow.
        """
        await self._apply_payment_succeeded(payment, receipt_obj=None, send_user_telegram=False)
