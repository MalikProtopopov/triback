"""Публичный статус платежа и опрос Moneta (fallback без Pay URL webhook)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.enums import PaymentStatus, ProductType
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.events import EventRegistration
from app.models.subscriptions import Payment
from app.schemas.subscriptions import PaymentStatusResponse
from app.services.payment_providers.moneta_client import MonetaPaymentProvider
from app.services.payment_webhook_service import PaymentWebhookService

logger = structlog.get_logger(__name__)


class PaymentStatusService:
    """Логика GET payment status и POST check-status (Moneta poll)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_payment_status_public(self, payment_id: UUID) -> PaymentStatusResponse:
        """Публичный статус платежа для страницы /payment/success (без авторизации)."""
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found")

        event_id: UUID | None = None
        event_title: str | None = None
        if payment.product_type == ProductType.EVENT and payment.event_registration_id:
            er_result = await self.db.execute(
                select(EventRegistration)
                .options(joinedload(EventRegistration.event))
                .where(EventRegistration.id == payment.event_registration_id)
            )
            er = er_result.scalar_one_or_none()
            if er and er.event:
                event_id = er.event_id
                event_title = er.event.title

        return PaymentStatusResponse(
            payment_id=payment.id,
            status=payment.status,
            product_type=payment.product_type,
            amount=float(payment.amount),
            created_at=payment.created_at,
            paid_at=payment.paid_at,
            event_id=event_id,
            event_title=event_title,
        )

    async def check_payment_status(self, user_id: UUID, payment_id: UUID) -> dict[str, Any]:
        """Опрос Moneta API для подтверждения оплаты (если Pay URL не пришёл)."""
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment not found")
        if payment.user_id != user_id:
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

        provider = MonetaPaymentProvider()
        try:
            op_info = await provider.get_operation_status(operation_id)
        except Exception as exc:
            logger.warning(
                "moneta_check_status_error", error=str(exc), operation_id=operation_id
            )
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
