"""Shared builders for payment webhook payloads in tests."""

from __future__ import annotations

from uuid import uuid4

from app.services.payment_providers.moneta_client import _md5


def moneta_pay_signature(
    mnt_id: str,
    txn_id: str,
    op_id: str,
    amount: str,
    secret: str,
) -> str:
    """MD5 for Moneta Pay URL (no MNT_COMMAND)."""
    return _md5(mnt_id, txn_id, op_id, amount, "RUB", "", "", secret)


def yookassa_notification(
    *,
    internal_payment_id: str,
    event: str = "payment.succeeded",
    external_id: str | None = None,
    object_status: str = "succeeded",
    extra_object_fields: dict | None = None,
) -> dict:
    """Minimal YooKassa-style JSON body (metadata links internal payment id)."""
    oid = external_id or f"yk-{uuid4().hex[:12]}"
    obj: dict = {
        "id": oid,
        "status": object_status,
        "metadata": {"internal_payment_id": internal_payment_id},
    }
    if extra_object_fields:
        obj.update(extra_object_fields)
    return {
        "type": "notification",
        "event": event,
        "object": obj,
    }
