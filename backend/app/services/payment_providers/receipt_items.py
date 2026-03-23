"""Map domain PaymentItem rows to provider-specific receipt line payloads."""

from __future__ import annotations

from typing import Any

from app.services.payment_providers.base import PaymentItem


def yookassa_receipt_items(items: list[PaymentItem]) -> list[dict[str, Any]]:
    """YooKassa receipt.items[] entries (54-FZ line items)."""
    return [
        {
            "description": item.name,
            "quantity": str(item.quantity),
            "amount": {"value": str(item.price), "currency": "RUB"},
            "vat_code": item.vat_code or 1,
            "payment_subject": item.payment_object,
            "payment_mode": item.payment_method,
        }
        for item in items
    ]
