"""Unit tests for PaymentApplicationService with a fake provider."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.subscriptions import Payment
from app.services.payment_application_service import PaymentApplicationService
from app.services.payment_providers.base import (
    CreatePaymentResult,
    PaymentItem,
    RefundResult,
    WebhookData,
)


class FakePaymentProvider:
    """Minimal PaymentProviderProtocol implementation for tests."""

    def __init__(self) -> None:
        self.last_kwargs: dict | None = None

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
        metadata: dict | None = None,
    ) -> CreatePaymentResult:
        self.last_kwargs = {
            "transaction_id": transaction_id,
            "items": items,
            "total_amount": total_amount,
            "description": description,
            "customer_email": customer_email,
            "return_url": return_url,
            "idempotency_key": idempotency_key,
            "metadata": metadata,
        }
        return CreatePaymentResult(
            external_id="ext-1",
            payment_url="https://pay.example/1",
            raw_response={"ok": True},
        )

    async def verify_webhook(self, request_data: dict) -> WebhookData:
        return WebhookData(
            event_type="test",
            external_id="",
            transaction_id="",
            amount=Decimal("0"),
            raw_data=request_data,
        )

    def build_webhook_success_response(self, request_data: dict) -> str:
        return "OK"

    async def create_refund(
        self,
        *,
        external_payment_id: str,
        amount: Decimal,
        items: list[PaymentItem] | None,
        description: str,
        idempotency_key: str,
    ) -> RefundResult:
        return RefundResult(external_id="r1", status="succeeded", raw_response={})

    async def get_operation_status(self, operation_id: str) -> dict:
        return {"status": "unknown"}


@pytest.mark.anyio
async def test_payment_application_service_delegates_to_provider() -> None:
    provider = FakePaymentProvider()
    svc = PaymentApplicationService(provider)
    payment = Payment(
        id=uuid4(),
        user_id=uuid4(),
        amount=100.0,
        product_type="subscription",
        payment_provider="yookassa",
        status="pending",
    )
    items = [PaymentItem(name="Plan", price=Decimal("100.00"))]
    result = await svc.create_redirect_payment(
        payment=payment,
        items=items,
        total_amount=Decimal("100.00"),
        customer_email="a@b.c",
        description="Test",
        idempotency_key="idem-1",
        metadata={"k": "v"},
    )
    assert result.external_id == "ext-1"
    assert result.payment_url == "https://pay.example/1"
    assert provider.last_kwargs is not None
    assert provider.last_kwargs["transaction_id"] == str(payment.id)
    assert provider.last_kwargs["idempotency_key"] == "idem-1"
    assert provider.last_kwargs["metadata"] == {"k": "v"}
    assert payment.external_payment_id == "ext-1"
    assert payment.external_payment_url == "https://pay.example/1"
