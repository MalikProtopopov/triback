"""Structural typing for payment providers (mirrors PaymentProvider ABC)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from app.services.payment_providers.base import (
    CreatePaymentResult,
    PaymentItem,
    RefundResult,
    WebhookData,
)


@runtime_checkable
class PaymentProviderProtocol(Protocol):
    """Provider-agnostic gateway — use for DI and tests without inheriting ABC."""

    async def create_payment(
        self,
        *,
        transaction_id: str,
        items: list[PaymentItem],
        total_amount: Decimal,
        description: str,
        customer_email: str,
        return_url: str,
        idempotency_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> CreatePaymentResult: ...

    async def verify_webhook(self, request_data: dict[str, Any]) -> WebhookData: ...

    def build_webhook_success_response(self, request_data: dict[str, Any]) -> str: ...

    async def create_refund(
        self,
        *,
        external_payment_id: str,
        amount: Decimal,
        items: list[PaymentItem] | None,
        description: str,
        idempotency_key: str,
    ) -> RefundResult: ...

    async def get_operation_status(self, operation_id: str) -> dict[str, Any]: ...
