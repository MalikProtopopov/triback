"""Unit tests for MonetaPaymentProvider."""

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
    monkeypatch.setattr("app.core.config.settings.MONETA_BPA_API_URL", "https://bpa.test/api")
    monkeypatch.setattr("app.core.config.settings.MONETA_BPA_KEY", "test-key")
    monkeypatch.setattr("app.core.config.settings.MONETA_BPA_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_CREDIT_ACCOUNT", "credit-acc")
    monkeypatch.setattr("app.core.config.settings.MONETA_DEBIT_ACCOUNT", "debit-acc")
    monkeypatch.setattr("app.core.config.settings.MONETA_SELLER_ACCOUNT", "seller-acc")
    monkeypatch.setattr("app.core.config.settings.MONETA_SELLER_INN", "1234567890")
    monkeypatch.setattr("app.core.config.settings.MONETA_SELLER_NAME", "Test Org")
    monkeypatch.setattr("app.core.config.settings.MONETA_SELLER_PHONE", "+79001234567")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "test-mnt-id")
    monkeypatch.setattr("app.core.config.settings.MONETA_ASSISTANT_URL", "https://moneta.test/assistant.htm")
    monkeypatch.setattr("app.core.config.settings.MONETA_DEMO_MODE", False)
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "webhook-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_SUCCESS_URL", "https://test.com/success")
    monkeypatch.setattr("app.core.config.settings.MONETA_FAIL_URL", "https://test.com/fail")
    monkeypatch.setattr("app.core.config.settings.MONETA_INPROGRESS_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_RETURN_URL", "https://test.com/return")
    monkeypatch.setattr("app.core.config.settings.MONETA_VAT_CODE", 1105)
    monkeypatch.setattr("app.core.config.settings.MONETA_PAYMENT_OBJECT", "service")
    monkeypatch.setattr("app.core.config.settings.MONETA_PAYMENT_METHOD", "full_payment")
    monkeypatch.setattr("app.core.config.settings.MONETA_FORM_VERSION", "v3")
    return MonetaPaymentProvider()


def test_md5_helper():
    result = _md5("a", "b", "c")
    expected = hashlib.md5(b"abc").hexdigest()
    assert result == expected


@pytest.mark.anyio
async def test_create_invoice_success(provider: MonetaPaymentProvider):
    mock_response = httpx.Response(
        200,
        json={"operation": 12345},
        request=httpx.Request("POST", "https://bpa.test/api/invoice"),
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
    assert result.external_id == "12345"
    assert "operationId=12345" in result.payment_url
    assert "version=v3" in result.payment_url


@pytest.mark.anyio
async def test_create_invoice_error(provider: MonetaPaymentProvider):
    mock_response = httpx.Response(
        400,
        json={"error": "Invalid account"},
        request=httpx.Request("POST", "https://bpa.test/api/invoice"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response), pytest.raises(ValueError, match="Moneta invoice error"):
        await provider.create_payment(
                transaction_id="txn-002",
                items=[PaymentItem(name="Test", price=Decimal("100"))],
                total_amount=Decimal("100"),
                description="Test",
                customer_email="user@test.com",
                return_url="https://test.com",
                idempotency_key="idem-002",
            )


@pytest.mark.anyio
async def test_create_invoice_multiple_items(provider: MonetaPaymentProvider):
    mock_response = httpx.Response(
        200,
        json={"operation": 67890},
        request=httpx.Request("POST", "https://bpa.test/api/invoice"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        result = await provider.create_payment(
            transaction_id="txn-003",
            items=[
                PaymentItem(name="Entry Fee", price=Decimal("5000.00")),
                PaymentItem(name="Annual Sub", price=Decimal("15000.00")),
            ],
            total_amount=Decimal("20000.00"),
            description="Entry + Sub",
            customer_email="user@test.com",
            return_url="https://test.com",
            idempotency_key="idem-003",
        )
    assert result.external_id == "67890"
    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["paymentAmount"] == 20000.00
    assert len(payload["inventory"]) == 2


@pytest.mark.anyio
async def test_create_invoice_demo_mode(provider: MonetaPaymentProvider):
    provider._demo_mode = True
    mock_response = httpx.Response(
        200,
        json={"operation": 99999},
        request=httpx.Request("POST", "https://bpa.test/api/invoice"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.create_payment(
            transaction_id="txn-004",
            items=[PaymentItem(name="Test", price=Decimal("100"))],
            total_amount=Decimal("100"),
            description="Demo",
            customer_email="user@test.com",
            return_url="https://test.com",
            idempotency_key="idem-004",
        )
    assert "demo.moneta.ru" in result.payment_url


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
    """Decimal conversion of a garbage MNT_AMOUNT should raise ValueError."""
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


@pytest.mark.anyio
async def test_create_invoice_retry_on_5xx(provider: MonetaPaymentProvider):
    """BPA returns 500 twice then 200 — the third attempt should succeed."""
    fail_resp = httpx.Response(
        500,
        text="Internal Server Error",
        request=httpx.Request("POST", "https://bpa.test/api/invoice"),
    )
    ok_resp = httpx.Response(
        200,
        json={"operation": 55555},
        request=httpx.Request("POST", "https://bpa.test/api/invoice"),
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
