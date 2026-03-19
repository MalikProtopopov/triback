"""Moneta MerchantAPI v2 payment provider implementation."""

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
_CONTENT_TYPE = "application/json;charset=UTF-8"

_DEMO_SERVICE_URL = "https://demo.moneta.ru/services"
_DEMO_ASSISTANT_URL = "https://demo.moneta.ru/assistant.htm"
_PROD_SERVICE_URL = "https://service.moneta.ru/services"


def _md5(*parts: str) -> str:
    return hashlib.md5("".join(parts).encode("utf-8")).hexdigest()


class MonetaPaymentProvider(PaymentProvider):
    """MerchantAPI v2 provider (JSON Envelope). Fiscalisation via Moneta dashboard."""

    def __init__(self) -> None:
        self._username = settings.MONETA_USERNAME
        self._password = settings.MONETA_PASSWORD
        self._service_url = settings.MONETA_SERVICE_URL
        self._payee_account = settings.MONETA_PAYEE_ACCOUNT
        self._payment_password = settings.MONETA_PAYMENT_PASSWORD
        self._mnt_id = settings.MONETA_MNT_ID
        self._assistant_url = settings.MONETA_ASSISTANT_URL
        self._demo_mode = settings.MONETA_DEMO_MODE
        self._webhook_secret = settings.MONETA_WEBHOOK_SECRET
        self._success_url = settings.MONETA_SUCCESS_URL
        self._fail_url = settings.MONETA_FAIL_URL
        self._inprogress_url = settings.MONETA_INPROGRESS_URL
        self._return_url = settings.MONETA_RETURN_URL
        self._form_version = settings.MONETA_FORM_VERSION

        if self._demo_mode:
            if self._service_url == _PROD_SERVICE_URL:
                self._service_url = _DEMO_SERVICE_URL
            if "demo" not in self._assistant_url:
                self._assistant_url = _DEMO_ASSISTANT_URL

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
        amount_str = f"{float(total_amount):.2f}"
        payment_url = self._build_payment_url(
            transaction_id=transaction_id,
            amount=amount_str,
        )

        return CreatePaymentResult(
            external_id="",
            payment_url=payment_url,
            raw_response={},
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
        refund: dict[str, Any] = {
            "transactionId": int(external_payment_id),
        }
        if amount:
            refund["amount"] = float(amount)
        if description:
            refund["description"] = description
        if self._payment_password:
            refund["paymentPassword"] = self._payment_password

        body = await self._api_request("RefundRequest", refund)
        resp = body["RefundResponse"]
        refund_id = str(resp.get("id", ""))
        attrs = {a["key"]: a["value"] for a in resp.get("attribute", [])}
        status = attrs.get("statusid", "unknown")
        return RefundResult(external_id=refund_id, status=status, raw_response=resp)

    async def get_operation_status(self, operation_id: str) -> dict[str, Any]:
        body = await self._api_request(
            "GetOperationDetailsByIdRequest", int(operation_id)
        )
        op = body["GetOperationDetailsByIdResponse"]["operation"]
        attrs = {a["key"]: a["value"] for a in op.get("attribute", [])}
        return {"id": op["id"], "status": attrs.get("statusid", "unknown"), "attributes": attrs}

    async def verify_webhook(self, request_data: dict[str, Any]) -> WebhookData:
        mnt_id = str(request_data.get("MNT_ID", ""))
        mnt_transaction_id = str(request_data.get("MNT_TRANSACTION_ID", ""))
        mnt_operation_id = str(request_data.get("MNT_OPERATION_ID", ""))
        mnt_amount = str(request_data.get("MNT_AMOUNT", ""))
        mnt_currency = str(request_data.get("MNT_CURRENCY_CODE", ""))
        mnt_subscriber_id = str(request_data.get("MNT_SUBSCRIBER_ID", ""))
        mnt_test_mode = str(request_data.get("MNT_TEST_MODE", ""))
        mnt_signature = str(request_data.get("MNT_SIGNATURE", ""))
        mnt_command = str(request_data.get("MNT_COMMAND", ""))

        if mnt_command:
            # Check URL: MD5(MNT_COMMAND + MNT_ID + MNT_TRANSACTION_ID + MNT_AMOUNT
            #   + MNT_CURRENCY_CODE + MNT_SUBSCRIBER_ID + MNT_TEST_MODE + secret)
            expected = _md5(
                mnt_command,
                mnt_id,
                mnt_transaction_id,
                mnt_amount,
                mnt_currency,
                mnt_subscriber_id,
                mnt_test_mode,
                self._webhook_secret,
            )
        else:
            # Pay URL: MD5(MNT_ID + MNT_TRANSACTION_ID + MNT_OPERATION_ID + MNT_AMOUNT
            #   + MNT_CURRENCY_CODE + MNT_SUBSCRIBER_ID + MNT_TEST_MODE + secret)
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payment_url(
        self,
        *,
        transaction_id: str,
        amount: str,
    ) -> str:
        """Build Moneta Assistant URL using the standard HTML-form approach.

        No operationId — Moneta creates the operation itself on form load,
        then calls Check URL and Pay URL as documented.
        """
        base = self._assistant_url
        test_mode = "1" if self._demo_mode else "0"

        url = f"{base}?MNT_ID={self._mnt_id}"
        url += f"&MNT_TRANSACTION_ID={transaction_id}"
        url += f"&MNT_AMOUNT={amount}"
        url += f"&MNT_CURRENCY_CODE=RUB"
        url += f"&MNT_TEST_MODE={test_mode}"

        if self._webhook_secret:
            sig = _md5(
                self._mnt_id,
                transaction_id,
                amount,
                "RUB",
                "",  # MNT_SUBSCRIBER_ID
                test_mode,
                self._webhook_secret,
            )
            url += f"&MNT_SIGNATURE={sig}"

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

    def _build_envelope(self, body_key: str, body_value: Any) -> dict[str, Any]:
        return {
            "Envelope": {
                "Header": {
                    "Security": {
                        "UsernameToken": {
                            "Username": self._username,
                            "Password": self._password,
                        }
                    }
                },
                "Body": {body_key: body_value},
            }
        }

    async def _api_request(self, body_key: str, body_value: Any) -> dict[str, Any]:
        """Send a MerchantAPI v2 JSON Envelope request with retries on 5xx/network errors."""
        envelope = self._build_envelope(body_key, body_value)
        last_exc: Exception | None = None

        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        self._service_url,
                        json=envelope,
                        headers={"Content-Type": _CONTENT_TYPE},
                    )
                if resp.status_code >= 500:
                    logger.warning(
                        "moneta_api_5xx",
                        status=resp.status_code,
                        attempt=attempt + 1,
                        body=resp.text[:500],
                    )
                    last_exc = httpx.HTTPStatusError(
                        f"Moneta API {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                else:
                    data = resp.json()
                    body = data.get("Envelope", {}).get("Body", {})
                    if "fault" in body:
                        fault = body["fault"]
                        code = fault.get("detail", {}).get("faultDetail", "unknown")
                        msg = fault.get("faultstring", "Unknown Moneta error")
                        raise ValueError(f"Moneta API error [{code}]: {msg}")
                    return body
            except httpx.HTTPError as exc:
                logger.warning(
                    "moneta_api_request_error",
                    error=str(exc),
                    attempt=attempt + 1,
                )
                last_exc = exc

            if attempt < len(RETRY_DELAYS) - 1:
                await asyncio.sleep(delay)

        raise last_exc or RuntimeError("Moneta API request failed after retries")
