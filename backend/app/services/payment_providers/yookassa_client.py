"""YooKassa payment provider — adapts the legacy client to PaymentProvider ABC."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

import httpx
import structlog

from app.core.config import settings
from app.services.payment_providers.base import (
    CreatePaymentResult,
    PaymentItem,
    PaymentProvider,
    RefundResult,
    WebhookData,
)

logger = structlog.get_logger(__name__)

RETRY_DELAYS = [1.0, 2.0, 4.0]


class YooKassaPaymentProvider(PaymentProvider):
    """Async HTTP client for YooKassa REST API v3."""

    def __init__(self) -> None:
        self._base_url = settings.YOOKASSA_API_URL
        self._auth = (settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)

    # ------------------------------------------------------------------
    # PaymentProvider interface
    # ------------------------------------------------------------------

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
    ) -> CreatePaymentResult:
        receipt_items = [
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
        receipt = {
            "customer": {"email": customer_email},
            "items": receipt_items,
        }
        payload: dict[str, Any] = {
            "amount": {"value": str(total_amount), "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description,
            "metadata": {**(metadata or {}), "internal_payment_id": transaction_id},
            "receipt": receipt,
        }
        headers = {"Idempotence-Key": idempotency_key}
        data = await self._request("POST", "/payments", json=payload, headers=headers)
        return CreatePaymentResult(
            external_id=data["id"],
            payment_url=data.get("confirmation", {}).get("confirmation_url", ""),
            raw_response=data,
        )

    async def verify_webhook(self, request_data: dict[str, Any]) -> WebhookData:
        event = request_data.get("event", "")
        obj = request_data.get("object", {})

        event_type = event
        if event == "payment.succeeded":
            event_type = "payment.succeeded"
        elif event == "payment.canceled":
            event_type = "payment.canceled"
        elif event == "refund.succeeded":
            event_type = "refund.succeeded"

        metadata = obj.get("metadata", {})
        return WebhookData(
            event_type=event_type,
            external_id=obj.get("id", ""),
            transaction_id=metadata.get("internal_payment_id", ""),
            amount=Decimal(obj.get("amount", {}).get("value", "0")),
            raw_data=request_data,
        )

    def build_webhook_success_response(self, request_data: dict[str, Any]) -> str:
        return ""

    async def create_refund(
        self,
        *,
        external_payment_id: str,
        amount: Decimal,
        items: list[PaymentItem] | None = None,
        description: str = "",
        idempotency_key: str = "",
    ) -> RefundResult:
        payload: dict[str, Any] = {
            "payment_id": external_payment_id,
            "amount": {"value": str(amount), "currency": "RUB"},
        }
        if description:
            payload["description"] = description
        headers = {"Idempotence-Key": idempotency_key} if idempotency_key else {}
        data = await self._request("POST", "/refunds", json=payload, headers=headers)
        return RefundResult(
            external_id=data.get("id", ""),
            status=data.get("status", ""),
            raw_response=data,
        )

    # ------------------------------------------------------------------
    # Low-level HTTP (kept from the legacy client)
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        last_exc: Exception | None = None

        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                async with httpx.AsyncClient(auth=self._auth, timeout=15.0) as client:
                    resp = await client.request(method, url, json=json, headers=headers or {})
                if resp.status_code < 500:
                    resp.raise_for_status()
                    return resp.json()  # type: ignore[no-any-return]

                logger.warning(
                    "yookassa_5xx",
                    status=resp.status_code,
                    attempt=attempt + 1,
                    body=resp.text[:500],
                )
                last_exc = httpx.HTTPStatusError(
                    f"YooKassa {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            except httpx.HTTPStatusError:
                raise
            except httpx.HTTPError as exc:
                logger.warning("yookassa_request_error", error=str(exc), attempt=attempt + 1)
                last_exc = exc

            if attempt < len(RETRY_DELAYS) - 1:
                await asyncio.sleep(delay)

        raise last_exc or RuntimeError("YooKassa request failed after retries")
