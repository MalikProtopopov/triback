"""Helpers to avoid logging raw PII (emails, etc.)."""

from __future__ import annotations

import hashlib
from typing import Any


def mask_email_for_log(email: str | None) -> str:
    """Return a non-reversible fingerprint + domain tail for correlation without storing raw email."""
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.strip().lower().partition("@")
    if not local or not domain:
        return "***"
    digest = hashlib.sha256(f"{local}@{domain}".encode()).hexdigest()[:12]
    return f"email_sha256_12={digest}@{domain}"


def moneta_params_for_log(params: dict[str, str]) -> dict[str, str | list[str]]:
    """Safe subset of Moneta webhook/query params (no MNT_SIGNATURE, no full amounts if desired)."""
    keys = sorted(params.keys())
    out: dict[str, str | list[str]] = {
        "keys": keys,
        "MNT_OPERATION_ID": (params.get("MNT_OPERATION_ID") or "")[:64],
        "MNT_TRANSACTION_ID": (params.get("MNT_TRANSACTION_ID") or "")[:64],
        "MNT_COMMAND": (params.get("MNT_COMMAND") or "")[:32],
        "MNT_ID": (params.get("MNT_ID") or "")[:64],
    }
    amt = params.get("MNT_AMOUNT")
    if amt:
        out["MNT_AMOUNT_present"] = "yes"
    return out


def yookassa_webhook_body_summary(body: dict[str, Any]) -> dict[str, Any]:
    """Minimal webhook payload fields for logs."""
    obj = body.get("object") or {}
    return {
        "event": str(body.get("event", ""))[:64],
        "object_id": str(obj.get("id", ""))[:80],
        "status": str(obj.get("status", ""))[:32],
    }


def moneta_receipt_body_summary(body: dict[str, Any]) -> dict[str, Any]:
    op = body.get("operation")
    return {
        "operation_present": bool(op),
        "has_receipt_url": bool(body.get("receipt")),
        "has_parentid": bool(body.get("parentid")),
    }
