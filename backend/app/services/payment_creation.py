"""Shared logic for creating payments via any PaymentProvider (Moneta / YooKassa)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.models.subscriptions import Payment
from app.services.payment_providers import PaymentItem
from app.services.payment_providers.base import CreatePaymentResult
from app.services.payment_providers.protocols import PaymentProviderProtocol


def get_payment_return_url() -> str:
    """Return URL passed to the payment provider after checkout."""
    if settings.PAYMENT_PROVIDER == "moneta":
        return settings.MONETA_RETURN_URL or settings.MONETA_SUCCESS_URL
    return settings.YOOKASSA_RETURN_URL


def apply_create_payment_result(payment: Payment, result: CreatePaymentResult) -> None:
    """Persist provider response on a pending Payment row (Moneta sets moneta_operation_id)."""
    payment.external_payment_id = result.external_id or None
    payment.external_payment_url = result.payment_url
    if settings.PAYMENT_PROVIDER == "moneta" and result.external_id:
        payment.moneta_operation_id = result.external_id


async def create_payment_via_provider(
    provider: PaymentProviderProtocol,
    payment: Payment,
    *,
    items: list[PaymentItem],
    total_amount: Decimal,
    description: str,
    customer_email: str,
    idempotency_key: str,
    metadata: dict[str, Any] | None = None,
) -> CreatePaymentResult:
    """Call provider.create_payment with the correct return URL and return the result."""
    result = await provider.create_payment(
        transaction_id=str(payment.id),
        items=items,
        total_amount=total_amount,
        description=description,
        customer_email=customer_email,
        return_url=get_payment_return_url(),
        idempotency_key=idempotency_key,
        metadata=metadata,
    )
    apply_create_payment_result(payment, result)
    return result
