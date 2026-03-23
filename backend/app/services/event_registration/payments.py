"""Create provider payment for an event registration."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EventRegistrationStatus, PaymentStatus
from app.models.events import Event, EventRegistration, EventTariff
from app.models.subscriptions import Payment
from app.services.payment_creation import create_payment_via_provider
from app.services.payment_providers import PaymentItem
from app.services.payment_providers.protocols import PaymentProviderProtocol


async def process_event_registration_payment(
    db: AsyncSession,
    provider: PaymentProviderProtocol,
    payment: Payment,
    event: Event,
    tariff: EventTariff,
    reg: EventRegistration,
    applied_price: float,
    receipt_email: str,
    fiscal_email: str | None,
) -> str | None:
    if applied_price <= 0:
        payment.status = PaymentStatus.SUCCEEDED
        reg.status = EventRegistrationStatus.CONFIRMED
        return None

    email_for_receipt = fiscal_email or receipt_email
    description = f"{event.title} — {tariff.name}"
    items = [PaymentItem(name=description, price=Decimal(str(applied_price)))]

    line_description = payment.description or description
    await create_payment_via_provider(
        provider,
        payment,
        items=items,
        total_amount=Decimal(str(applied_price)),
        description=line_description,
        customer_email=email_for_receipt,
        idempotency_key=payment.idempotency_key or "",
        metadata={
            "product_type": "event",
            "user_id": str(payment.user_id),
            "event_id": str(event.id),
            "registration_id": str(reg.id),
        },
    )
    return payment.external_payment_url
