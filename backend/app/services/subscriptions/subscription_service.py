"""SubscriptionService — facade for subscription and payment operations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.payments import ManualPaymentRequest, ManualPaymentResponse, PaymentListResponse
from app.schemas.subscriptions import (
    PaymentStatusResponse,
    PayResponse,
    SubscriptionStatusResponse,
)
from app.services.payment_admin_service import PaymentAdminService
from app.services.payment_status_service import PaymentStatusService
from app.services.payment_user_service import PaymentUserService
from app.services.payment_webhook_service import PaymentWebhookService
from app.services.subscriptions.subscription_pay import SubscriptionPayService
from app.services.subscriptions.subscription_status import SubscriptionUserStatusService


class SubscriptionService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis
        # Resolve via shim so tests can patch ``app.services.subscription_service.get_provider``.
        import app.services.subscription_service as _subscription_shim

        self.provider = _subscription_shim.get_provider()
        self._webhook = PaymentWebhookService(db)
        self._admin = PaymentAdminService(db)
        self._user = PaymentUserService(db)
        self._payment_status = PaymentStatusService(db)
        self._pay = SubscriptionPayService(db, redis, self.provider)
        self._sub_status = SubscriptionUserStatusService(db)

    async def pay(self, user_id: UUID, plan_id: UUID, idempotency_key: str) -> PayResponse:
        return await self._pay.pay(user_id, plan_id, idempotency_key)

    async def pay_arrear(
        self, user_id: UUID, arrear_id: UUID, idempotency_key: str
    ) -> PayResponse:
        return await self._pay.pay_arrear(user_id, arrear_id, idempotency_key)

    async def get_status(self, user_id: UUID) -> SubscriptionStatusResponse:
        return await self._sub_status.get_status(user_id)

    async def handle_webhook(self, body: dict[str, Any], client_ip: str) -> None:
        return await self._webhook.handle_webhook(body, client_ip)

    async def list_user_payments(
        self, user_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        return await self._user.list_user_payments(user_id, limit=limit, offset=offset)

    async def get_user_receipt(
        self, user_id: UUID, payment_id: UUID
    ) -> dict[str, Any]:
        return await self._user.get_user_receipt(user_id, payment_id)

    async def list_payments(self, **kwargs: Any) -> PaymentListResponse:
        return await self._admin.list_payments(**kwargs)

    async def create_manual_payment(
        self, admin_id: UUID, body: ManualPaymentRequest
    ) -> ManualPaymentResponse:
        return await self._admin.create_manual_payment(admin_id, body)

    async def initiate_refund(
        self, payment_id: UUID, amount: float | None, reason: str
    ) -> dict[str, Any]:
        return await self._admin.initiate_refund(payment_id, amount, reason)

    async def cancel_payment(self, payment_id: UUID, reason: str) -> dict[str, Any]:
        return await self._admin.cancel_payment(payment_id, reason)

    async def get_payment_status_public(
        self, payment_id: UUID
    ) -> PaymentStatusResponse:
        return await self._payment_status.get_payment_status_public(payment_id)

    async def check_payment_status(
        self, user_id: UUID, payment_id: UUID
    ) -> dict[str, Any]:
        return await self._payment_status.check_payment_status(user_id, payment_id)
