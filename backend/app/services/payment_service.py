"""YooKassa HTTP client with retry logic."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

RETRY_DELAYS = [1.0, 2.0, 4.0]


class YooKassaClient:
    """Async HTTP client for YooKassa REST API v3."""

    def __init__(self) -> None:
        self._base_url = settings.YOOKASSA_API_URL
        self._auth = (settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)

    async def create_payment(
        self,
        *,
        amount: Decimal,
        description: str,
        metadata: dict[str, Any],
        idempotency_key: str,
        return_url: str,
        receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "amount": {"value": str(amount), "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description,
            "metadata": metadata,
        }
        if receipt:
            payload["receipt"] = receipt
        headers = {"Idempotence-Key": idempotency_key}
        return await self._request("POST", "/payments", json=payload, headers=headers)

    async def get_payment(self, external_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/payments/{external_id}")

    async def create_refund(
        self,
        *,
        payment_id: str,
        amount: Decimal,
        description: str = "",
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "payment_id": payment_id,
            "amount": {"value": str(amount), "currency": "RUB"},
        }
        if description:
            payload["description"] = description
        headers = {"Idempotence-Key": idempotency_key}
        return await self._request("POST", "/refunds", json=payload, headers=headers)

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
                    resp = await client.request(
                        method, url, json=json, headers=headers or {}
                    )
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
