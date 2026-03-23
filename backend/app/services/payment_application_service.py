"""Application-level payment orchestration with an injectable provider (Protocol)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models.subscriptions import Payment
from app.services.payment_creation import create_payment_via_provider
from app.services.payment_providers.base import CreatePaymentResult, PaymentItem
from app.services.payment_providers.protocols import PaymentProviderProtocol


class PaymentApplicationService:
    """Thin wrapper around create_payment_via_provider for DI/testing."""

    def __init__(self, provider: PaymentProviderProtocol) -> None:
        self._provider = provider

    async def create_redirect_payment(
        self,
        *,
        payment: Payment,
        items: list[PaymentItem],
        total_amount: Decimal,
        customer_email: str,
        description: str,
        idempotency_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> CreatePaymentResult:
        return await create_payment_via_provider(
            self._provider,
            payment,
            items=items,
            total_amount=total_amount,
            description=description,
            customer_email=customer_email,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )
