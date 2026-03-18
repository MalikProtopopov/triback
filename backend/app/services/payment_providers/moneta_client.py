"""Moneta / BPA PayAnyWay payment provider implementation."""

from __future__ import annotations

import asyncio
import hashlib
from decimal import Decimal
from typing import Any
from urllib.parse import quote

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


def _md5(*parts: str) -> str:
    return hashlib.md5("".join(parts).encode("utf-8")).hexdigest()


class MonetaPaymentProvider(PaymentProvider):
    """BPA PayAnyWay API provider with native 54-FZ fiscalisation."""

    def __init__(self) -> None:
        self._bpa_url = settings.MONETA_BPA_API_URL
        self._bpa_key = settings.MONETA_BPA_KEY
        self._bpa_secret = settings.MONETA_BPA_SECRET
        self._credit_account = settings.MONETA_CREDIT_ACCOUNT
        self._debit_account = settings.MONETA_DEBIT_ACCOUNT
        self._seller_account = settings.MONETA_SELLER_ACCOUNT
        self._seller_inn = settings.MONETA_SELLER_INN
        self._seller_name = settings.MONETA_SELLER_NAME
        self._seller_phone = settings.MONETA_SELLER_PHONE
        self._mnt_id = settings.MONETA_MNT_ID
        self._assistant_url = settings.MONETA_ASSISTANT_URL
        self._demo_mode = settings.MONETA_DEMO_MODE
        self._webhook_secret = settings.MONETA_WEBHOOK_SECRET
        self._success_url = settings.MONETA_SUCCESS_URL
        self._fail_url = settings.MONETA_FAIL_URL
        self._inprogress_url = settings.MONETA_INPROGRESS_URL
        self._return_url = settings.MONETA_RETURN_URL
        self._vat_code = settings.MONETA_VAT_CODE
        self._payment_object = settings.MONETA_PAYMENT_OBJECT
        self._payment_method = settings.MONETA_PAYMENT_METHOD
        self._form_version = settings.MONETA_FORM_VERSION

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
        signature = _md5(self._debit_account or "", transaction_id, self._bpa_secret)

        inventory = [
            {
                "sellerAccount": self._seller_account,
                "sellerInn": self._seller_inn,
                "sellerName": self._seller_name,
                "sellerPhone": self._seller_phone,
                "productName": item.name,
                "productQuantity": item.quantity,
                "productPrice": float(item.price),
                "productVatCode": item.vat_code or self._vat_code,
                "po": item.payment_object or self._payment_object,
                "pm": item.payment_method or self._payment_method,
            }
            for item in items
        ]

        payload: dict[str, Any] = {
            "signature": signature,
            "paymentAmount": float(total_amount),
            "creditMntAccount": self._credit_account,
            "mntTransactionId": transaction_id,
            "customerEmail": customer_email,
            "inventory": inventory,
        }
        if self._debit_account:
            payload["debitMntAccount"] = self._debit_account

        url = f"{self._bpa_url}/invoice?key={self._bpa_key}"
        data = await self._bpa_request(url, payload)

        if "error" in data:
            raise ValueError(f"Moneta invoice error: {data['error']}")

        operation_id = str(data["operation"])
        payment_url = self._build_payment_url(operation_id)

        return CreatePaymentResult(
            external_id=operation_id,
            payment_url=payment_url,
            raw_response=data,
        )

    async def verify_webhook(self, request_data: dict[str, Any]) -> WebhookData:
        mnt_id = str(request_data.get("MNT_ID", ""))
        mnt_transaction_id = str(request_data.get("MNT_TRANSACTION_ID", ""))
        mnt_operation_id = str(request_data.get("MNT_OPERATION_ID", ""))
        mnt_amount = str(request_data.get("MNT_AMOUNT", ""))
        mnt_currency = str(request_data.get("MNT_CURRENCY_CODE", ""))
        mnt_subscriber_id = str(request_data.get("MNT_SUBSCRIBER_ID", ""))
        mnt_test_mode = str(request_data.get("MNT_TEST_MODE", ""))
        mnt_signature = str(request_data.get("MNT_SIGNATURE", ""))

        expected = _md5(
            mnt_id,
            mnt_transaction_id,
            mnt_operation_id,
            mnt_amount,
            mnt_currency,
            mnt_subscriber_id,
            mnt_test_mode,
            self._webhook_secret,
        )

        if mnt_signature.lower() != expected.lower():
            logger.warning(
                "moneta_invalid_signature",
                expected_prefix=expected[:8],
                received_prefix=mnt_signature[:8],
                mnt_transaction_id=mnt_transaction_id,
            )
            raise ValueError("Invalid Moneta webhook signature")

        try:
            parsed_amount = Decimal(mnt_amount) if mnt_amount else Decimal(0)
        except Exception:
            raise ValueError(f"Invalid MNT_AMOUNT: {mnt_amount!r}")

        return WebhookData(
            event_type="payment.succeeded",
            external_id=mnt_operation_id,
            transaction_id=mnt_transaction_id,
            amount=parsed_amount,
            raw_data=request_data,
        )

    def build_webhook_success_response(self, request_data: dict[str, Any]) -> str:
        return "SUCCESS"

    def build_check_response(
        self,
        mnt_id: str,
        mnt_transaction_id: str,
        result_code: str,
        amount: str | None = None,
    ) -> str:
        """Build XML response for Check URL requests."""
        sig = _md5(result_code, mnt_id, mnt_transaction_id, self._webhook_secret)
        amount_tag = f"\n  <MNT_AMOUNT>{amount}</MNT_AMOUNT>" if amount else ""
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<MNT_RESPONSE>\n"
            f"  <MNT_ID>{mnt_id}</MNT_ID>\n"
            f"  <MNT_TRANSACTION_ID>{mnt_transaction_id}</MNT_TRANSACTION_ID>\n"
            f"  <MNT_RESULT_CODE>{result_code}</MNT_RESULT_CODE>"
            f"{amount_tag}\n"
            f"  <MNT_SIGNATURE>{sig}</MNT_SIGNATURE>\n"
            "</MNT_RESPONSE>"
        )

    async def create_refund(
        self,
        *,
        external_payment_id: str,
        amount: Decimal,
        items: list[PaymentItem] | None = None,
        description: str = "",
        idempotency_key: str = "",
    ) -> RefundResult:
        raise NotImplementedError("Moneta refunds via MerchantAPI — TODO")

    # ------------------------------------------------------------------
    # BPA helper operations
    # ------------------------------------------------------------------

    async def confirm_operation(self, operation_id: str) -> dict[str, Any]:
        sig = _md5(operation_id, self._bpa_secret)
        url = f"{self._bpa_url}/confirmoperation?key={self._bpa_key}"
        data = await self._bpa_request(url, {"signature": sig, "operation": operation_id})
        if "error" in data:
            raise ValueError(f"Moneta confirm_operation error: {data['error']}")
        return data

    async def cancel_operation(self, operation_id: str) -> dict[str, Any]:
        sig = _md5(operation_id, self._bpa_secret)
        url = f"{self._bpa_url}/canceloperation?key={self._bpa_key}"
        data = await self._bpa_request(url, {"signature": sig, "operation": operation_id})
        if "error" in data:
            raise ValueError(f"Moneta cancel_operation error: {data['error']}")
        return data

    async def cancel_invoice(self, operation_id: str, description: str = "") -> dict[str, Any]:
        sig = _md5(operation_id, self._bpa_secret)
        url = f"{self._bpa_url}/cancelinvoice?key={self._bpa_key}"
        payload: dict[str, Any] = {"signature": sig, "operation": operation_id}
        if description:
            payload["description"] = description
        data = await self._bpa_request(url, payload)
        if "error" in data:
            raise ValueError(f"Moneta cancel_invoice error: {data['error']}")
        return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payment_url(self, operation_id: str) -> str:
        base = "https://demo.moneta.ru/assistant.htm" if self._demo_mode else self._assistant_url
        url = f"{base}?operationId={operation_id}"
        if self._form_version:
            url += f"&version={self._form_version}"
        if self._success_url:
            url += f"&MNT_SUCCESS_URL={quote(self._success_url, safe='')}"
        if self._fail_url:
            url += f"&MNT_FAIL_URL={quote(self._fail_url, safe='')}"
        if self._inprogress_url:
            url += f"&MNT_INPROGRESS_URL={quote(self._inprogress_url, safe='')}"
        if self._return_url:
            url += f"&MNT_RETURN_URL={quote(self._return_url, safe='')}"
        return url

    async def _bpa_request(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload)
                if resp.status_code < 500:
                    data = resp.json()
                    if resp.status_code >= 400:
                        logger.warning(
                            "moneta_bpa_error",
                            status=resp.status_code,
                            body=data,
                        )
                    return data  # type: ignore[no-any-return]
                logger.warning(
                    "moneta_bpa_5xx",
                    status=resp.status_code,
                    attempt=attempt + 1,
                    body=resp.text[:500],
                )
                last_exc = httpx.HTTPStatusError(
                    f"Moneta BPA {resp.status_code}", request=resp.request, response=resp
                )
            except httpx.HTTPError as exc:
                logger.warning("moneta_bpa_request_error", error=str(exc), attempt=attempt + 1)
                last_exc = exc

            if attempt < len(RETRY_DELAYS) - 1:
                await asyncio.sleep(delay)

        raise last_exc or RuntimeError("Moneta BPA request failed after retries")
