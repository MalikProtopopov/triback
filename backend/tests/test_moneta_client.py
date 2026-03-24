"""Unit tests for MonetaPaymentProvider (MerchantAPI v2)."""

from __future__ import annotations

import hashlib
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.payment_providers.base import PaymentItem
from app.services.payment_providers.moneta_client import MonetaPaymentProvider, _md5


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> MonetaPaymentProvider:
    monkeypatch.setattr("app.core.config.settings.MONETA_USERNAME", "test-user")
    monkeypatch.setattr("app.core.config.settings.MONETA_PASSWORD", "test-pass")
    monkeypatch.setattr("app.core.config.settings.MONETA_SERVICE_URL", "https://api.test/services")
    monkeypatch.setattr("app.core.config.settings.MONETA_PAYEE_ACCOUNT", "12345678")
    monkeypatch.setattr("app.core.config.settings.MONETA_PAYMENT_PASSWORD", "pay-pass")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "test-mnt-id")
    monkeypatch.setattr("app.core.config.settings.MONETA_ASSISTANT_URL", "https://test.payanyway.ru/assistant.htm")
    monkeypatch.setattr("app.core.config.settings.MONETA_DEMO_MODE", False)
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "webhook-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_SUCCESS_URL", "https://test.com/success")
    monkeypatch.setattr("app.core.config.settings.MONETA_FAIL_URL", "https://test.com/fail")
    monkeypatch.setattr("app.core.config.settings.MONETA_INPROGRESS_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_RETURN_URL", "https://test.com/return")
    monkeypatch.setattr("app.core.config.settings.MONETA_FORM_VERSION", "v3")
    return MonetaPaymentProvider()


def test_md5_helper():
    result = _md5("a", "b", "c")
    expected = hashlib.md5(b"abc").hexdigest()
    assert result == expected


# ------------------------------------------------------------------
# create_payment (InvoiceRequest)
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_invoice_success(provider: MonetaPaymentProvider):
    mock_response = httpx.Response(
        200,
        json={"Envelope": {"Body": {"InvoiceResponse": {
            "transaction": 328498,
            "dateTime": "2026-03-17T10:00:00.000+0300",
            "status": "CREATED",
            "clientTransaction": "txn-001",
        }}}},
        request=httpx.Request("POST", "https://api.test/services"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.create_payment(
            transaction_id="txn-001",
            items=[PaymentItem(name="Annual Subscription", price=Decimal("15000.00"))],
            total_amount=Decimal("15000.00"),
            description="Test payment",
            customer_email="user@test.com",
            return_url="https://test.com/return",
            idempotency_key="idem-001",
        )
    assert result.external_id == "328498"
    assert "MNT_TRANSACTION_ID=txn-001" in result.payment_url
    assert "version=v3" in result.payment_url


@pytest.mark.anyio
async def test_create_invoice_sends_correct_envelope(provider: MonetaPaymentProvider):
    mock_response = httpx.Response(
        200,
        json={"Envelope": {"Body": {"InvoiceResponse": {
            "transaction": 100, "status": "CREATED",
        }}}},
        request=httpx.Request("POST", "https://api.test/services"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        await provider.create_payment(
            transaction_id="txn-envelope",
            items=[PaymentItem(name="Test", price=Decimal("500"))],
            total_amount=Decimal("500"),
            description="Envelope check",
            customer_email="user@test.com",
            return_url="https://test.com",
            idempotency_key="idem-env",
        )

    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    envelope = payload["Envelope"]

    assert envelope["Header"]["Security"]["UsernameToken"]["Username"] == "test-user"
    assert envelope["Header"]["Security"]["UsernameToken"]["Password"] == "test-pass"
    body = envelope["Body"]["InvoiceRequest"]
    assert body["version"] == "VERSION_2"
    assert body["payer"] == "card"
    assert body["payee"] == "12345678"
    assert body["amount"] == 500.0
    assert body["clientTransaction"] == "txn-envelope"
    assert body["description"] == "Envelope check"

    headers = call_kwargs.kwargs.get("headers", {})
    assert headers.get("Content-Type") == "application/json;charset=UTF-8"


@pytest.mark.anyio
async def test_create_invoice_fault_response(provider: MonetaPaymentProvider):
    mock_response = httpx.Response(
        200,
        json={"Envelope": {"Body": {"fault": {
            "faultcode": "Client",
            "faultstring": "Invalid account",
            "detail": {"faultDetail": "500.1.5"},
        }}}},
        request=httpx.Request("POST", "https://api.test/services"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response), pytest.raises(ValueError, match="Moneta API error"):
        await provider.create_payment(
            transaction_id="txn-err",
            items=[PaymentItem(name="Test", price=Decimal("100"))],
            total_amount=Decimal("100"),
            description="Test",
            customer_email="user@test.com",
            return_url="https://test.com",
            idempotency_key="idem-err",
        )


@pytest.mark.anyio
async def test_create_invoice_multiple_items(provider: MonetaPaymentProvider):
    """Multiple items should still produce a single InvoiceRequest with total amount."""
    mock_response = httpx.Response(
        200,
        json={"Envelope": {"Body": {"InvoiceResponse": {
            "transaction": 67890, "status": "CREATED",
        }}}},
        request=httpx.Request("POST", "https://api.test/services"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        result = await provider.create_payment(
            transaction_id="txn-multi",
            items=[
                PaymentItem(name="Entry Fee", price=Decimal("5000.00")),
                PaymentItem(name="Annual Sub", price=Decimal("15000.00")),
            ],
            total_amount=Decimal("20000.00"),
            description="Entry + Sub",
            customer_email="user@test.com",
            return_url="https://test.com",
            idempotency_key="idem-multi",
        )
    assert result.external_id == "67890"
    payload = (mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json"))
    body = payload["Envelope"]["Body"]["InvoiceRequest"]
    assert body["version"] == "VERSION_2"
    assert body["payer"] == "card"
    assert body["amount"] == 20000.0


@pytest.mark.anyio
async def test_create_invoice_demo_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.core.config.settings.MONETA_USERNAME", "demo-user")
    monkeypatch.setattr("app.core.config.settings.MONETA_PASSWORD", "demo-pass")
    monkeypatch.setattr("app.core.config.settings.MONETA_SERVICE_URL", "https://service.moneta.ru/services")
    monkeypatch.setattr("app.core.config.settings.MONETA_PAYEE_ACCOUNT", "99999")
    monkeypatch.setattr("app.core.config.settings.MONETA_PAYMENT_PASSWORD", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-demo")
    monkeypatch.setattr("app.core.config.settings.MONETA_ASSISTANT_URL", "https://www.payanyway.ru/assistant.htm")
    monkeypatch.setattr("app.core.config.settings.MONETA_DEMO_MODE", True)
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "s")
    monkeypatch.setattr("app.core.config.settings.MONETA_SUCCESS_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_FAIL_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_INPROGRESS_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_RETURN_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_FORM_VERSION", "v3")

    p = MonetaPaymentProvider()
    assert p._service_url == "https://demo.moneta.ru/services"
    assert p._assistant_url == "https://demo.moneta.ru/assistant.htm"

    mock_response = httpx.Response(
        200,
        json={"Envelope": {"Body": {"InvoiceResponse": {"transaction": 99999, "status": "CREATED"}}}},
        request=httpx.Request("POST", "https://demo.moneta.ru/services"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await p.create_payment(
            transaction_id="txn-demo",
            items=[PaymentItem(name="Test", price=Decimal("100"))],
            total_amount=Decimal("100"),
            description="Demo",
            customer_email="user@test.com",
            return_url="https://test.com",
            idempotency_key="idem-demo",
        )
    assert "demo.moneta.ru" in result.payment_url


# ------------------------------------------------------------------
# create_refund (RefundRequest)
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_refund_success(provider: MonetaPaymentProvider):
    mock_response = httpx.Response(
        200,
        json={"Envelope": {"Body": {"RefundResponse": {
            "id": 102314550,
            "attribute": [
                {"value": "102314549", "key": "parentid"},
                {"value": "SUCCEED", "key": "statusid"},
                {"value": "1", "key": "isrefund"},
            ],
        }}}},
        request=httpx.Request("POST", "https://api.test/services"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        result = await provider.create_refund(
            external_payment_id="102314549",
            amount=Decimal("500.00"),
            description="Test refund",
        )
    assert result.external_id == "102314550"
    assert result.status == "SUCCEED"

    payload = (mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json"))
    refund_body = payload["Envelope"]["Body"]["RefundRequest"]
    assert refund_body["transactionId"] == 102314549
    assert refund_body["amount"] == 500.0
    assert refund_body["paymentPassword"] == "pay-pass"


# ------------------------------------------------------------------
# get_operation_status
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_operation_status(provider: MonetaPaymentProvider):
    mock_response = httpx.Response(
        200,
        json={"Envelope": {"Body": {"GetOperationDetailsByIdResponse": {"operation": {
            "id": 101370592,
            "attribute": [
                {"value": "SUCCEED", "key": "statusid"},
                {"value": "RUB", "key": "sourcecurrencycode"},
                {"value": "2.02", "key": "sourceamount"},
            ],
        }}}}},
        request=httpx.Request("POST", "https://api.test/services"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        result = await provider.get_operation_status("101370592")

    assert result["id"] == 101370592
    assert result["status"] == "SUCCEED"
    assert result["attributes"]["sourceamount"] == "2.02"

    payload = (mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json"))
    assert payload["Envelope"]["Body"]["GetOperationDetailsByIdRequest"] == 101370592


# ------------------------------------------------------------------
# verify_webhook (unchanged from BPA — same format)
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_verify_webhook_valid_signature(provider: MonetaPaymentProvider):
    mnt_id = "test-mnt-id"
    txn_id = "txn-001"
    op_id = "12345"
    amount = "15000.00"
    currency = "RUB"
    subscriber_id = ""
    test_mode = ""
    expected_sig = _md5(mnt_id, txn_id, op_id, amount, currency, subscriber_id, test_mode, "webhook-secret")

    data = {
        "MNT_ID": mnt_id,
        "MNT_TRANSACTION_ID": txn_id,
        "MNT_OPERATION_ID": op_id,
        "MNT_AMOUNT": amount,
        "MNT_CURRENCY_CODE": currency,
        "MNT_SUBSCRIBER_ID": subscriber_id,
        "MNT_TEST_MODE": test_mode,
        "MNT_SIGNATURE": expected_sig,
    }
    result = await provider.verify_webhook(data)
    assert result.transaction_id == txn_id
    assert result.external_id == op_id
    assert result.amount == Decimal("15000.00")


@pytest.mark.anyio
async def test_verify_webhook_invalid_signature(provider: MonetaPaymentProvider):
    data = {
        "MNT_ID": "test-mnt-id",
        "MNT_TRANSACTION_ID": "txn-001",
        "MNT_OPERATION_ID": "12345",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": "wrong-signature",
    }
    with pytest.raises(ValueError, match="Invalid Moneta webhook signature"):
        await provider.verify_webhook(data)


@pytest.mark.anyio
async def test_verify_webhook_missing_fields(provider: MonetaPaymentProvider):
    data = {"MNT_SIGNATURE": "something"}
    with pytest.raises(ValueError):
        await provider.verify_webhook(data)


def test_build_check_response(provider: MonetaPaymentProvider):
    xml = provider.build_check_response("mnt-1", "txn-1", "200", amount="15000.00")
    assert "<MNT_RESULT_CODE>200</MNT_RESULT_CODE>" in xml
    assert "<MNT_AMOUNT>15000.00</MNT_AMOUNT>" in xml
    assert "<MNT_SIGNATURE>" in xml


def test_build_webhook_success_response(provider: MonetaPaymentProvider):
    assert provider.build_webhook_success_response({}) == "SUCCESS"


@pytest.mark.anyio
async def test_verify_webhook_invalid_amount(provider: MonetaPaymentProvider):
    mnt_id = "test-mnt-id"
    txn_id = "txn-bad"
    op_id = "99999"
    amount = "NOT_A_NUMBER"
    currency = "RUB"
    subscriber_id = ""
    test_mode = ""
    sig = _md5(mnt_id, txn_id, op_id, amount, currency, subscriber_id, test_mode, "webhook-secret")

    data = {
        "MNT_ID": mnt_id,
        "MNT_TRANSACTION_ID": txn_id,
        "MNT_OPERATION_ID": op_id,
        "MNT_AMOUNT": amount,
        "MNT_CURRENCY_CODE": currency,
        "MNT_SUBSCRIBER_ID": subscriber_id,
        "MNT_TEST_MODE": test_mode,
        "MNT_SIGNATURE": sig,
    }
    with pytest.raises(ValueError, match="Invalid MNT_AMOUNT"):
        await provider.verify_webhook(data)


# ------------------------------------------------------------------
# Retry on 5xx
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_invoice_retry_on_5xx(provider: MonetaPaymentProvider):
    """API returns 500 twice then 200 — the third attempt should succeed."""
    fail_resp = httpx.Response(
        500,
        text="Internal Server Error",
        request=httpx.Request("POST", "https://api.test/services"),
    )
    ok_resp = httpx.Response(
        200,
        json={"Envelope": {"Body": {"InvoiceResponse": {"transaction": 55555, "status": "CREATED"}}}},
        request=httpx.Request("POST", "https://api.test/services"),
    )

    mock_post = AsyncMock(side_effect=[fail_resp, fail_resp, ok_resp])
    with patch("httpx.AsyncClient.post", mock_post), patch("asyncio.sleep", new_callable=AsyncMock):
        result = await provider.create_payment(
            transaction_id="txn-retry",
            items=[PaymentItem(name="Test", price=Decimal("100"))],
            total_amount=Decimal("100"),
            description="Retry test",
            customer_email="user@test.com",
            return_url="https://test.com",
            idempotency_key="idem-retry",
        )
    assert result.external_id == "55555"
    assert mock_post.call_count == 3
