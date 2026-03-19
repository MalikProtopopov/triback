"""Abstract payment provider interface and shared data classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class PaymentItem:
    """Single line item in a payment (maps to inventory / receipt)."""

    name: str
    price: Decimal
    quantity: int = 1
    vat_code: int | None = None
    payment_object: str = "service"
    payment_method: str = "full_payment"


@dataclass
class CreatePaymentResult:
    """Result returned after creating a payment at the provider."""

    external_id: str
    payment_url: str
    raw_response: dict = field(default_factory=dict)


@dataclass
class WebhookData:
    """Parsed incoming webhook payload."""

    event_type: str
    external_id: str
    transaction_id: str
    amount: Decimal
    raw_data: dict = field(default_factory=dict)


@dataclass
class RefundResult:
    """Result returned after creating a refund at the provider."""

    external_id: str
    status: str
    raw_response: dict = field(default_factory=dict)


class PaymentProvider(ABC):
    """Provider-agnostic payment gateway interface."""

    @abstractmethod
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

    @abstractmethod
    async def verify_webhook(self, request_data: dict[str, Any]) -> WebhookData: ...

    @abstractmethod
    def build_webhook_success_response(self, request_data: dict[str, Any]) -> str:
        """Build an HTTP response body for a successfully processed webhook."""
        ...

    @abstractmethod
    async def create_refund(
        self,
        *,
        external_payment_id: str,
        amount: Decimal,
        items: list[PaymentItem] | None = None,
        description: str = "",
        idempotency_key: str = "",
    ) -> RefundResult: ...

    async def get_operation_status(self, operation_id: str) -> dict[str, Any]:
        """Query the payment provider for operation details. Optional — not all providers support this."""
        raise NotImplementedError
