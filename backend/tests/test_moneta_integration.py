"""Integration tests against the real Moneta MerchantAPI v2.

These tests call ``service.moneta.ru`` (or ``demo.moneta.ru`` if
MONETA_DEMO_MODE=true) and therefore require valid credentials in
environment variables.  They are auto-skipped when credentials are
absent and must be explicitly selected with ``-m integration``.

Run:
    MONETA_USERNAME=... MONETA_PASSWORD=... MONETA_PAYEE_ACCOUNT=... \
        pytest tests/test_moneta_integration.py -m integration -v
"""

from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest

from app.services.payment_providers.base import PaymentItem
from app.services.payment_providers.moneta_client import MonetaPaymentProvider

_HAS_CREDS = bool(os.getenv("MONETA_USERNAME"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _HAS_CREDS, reason="MONETA_USERNAME env var not set"),
]


@pytest.fixture
def real_provider(monkeypatch: pytest.MonkeyPatch) -> MonetaPaymentProvider:
    """Build a MonetaPaymentProvider from real env vars."""
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_USERNAME",
        os.environ.get("MONETA_USERNAME", ""),
    )
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_PASSWORD",
        os.environ.get("MONETA_PASSWORD", ""),
    )
    svc_url = os.environ.get("MONETA_SERVICE_URL", "https://service.moneta.ru/services")
    monkeypatch.setattr("app.core.config.settings.MONETA_SERVICE_URL", svc_url)
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_PAYEE_ACCOUNT",
        os.environ.get("MONETA_PAYEE_ACCOUNT", ""),
    )
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_PAYMENT_PASSWORD",
        os.environ.get("MONETA_PAYMENT_PASSWORD", ""),
    )
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", os.environ.get("MONETA_MNT_ID", ""))
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_ASSISTANT_URL",
        os.environ.get("MONETA_ASSISTANT_URL", "https://www.payanyway.ru/assistant.htm"),
    )
    demo = os.environ.get("MONETA_DEMO_MODE", "false").lower() in ("1", "true", "yes")
    monkeypatch.setattr("app.core.config.settings.MONETA_DEMO_MODE", demo)
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", os.environ.get("MONETA_WEBHOOK_SECRET", ""))
    monkeypatch.setattr("app.core.config.settings.MONETA_SUCCESS_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_FAIL_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_INPROGRESS_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_RETURN_URL", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_FORM_VERSION", "v3")
    return MonetaPaymentProvider()


# ------------------------------------------------------------------
# 1. Create invoice against real API
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_real_create_invoice(real_provider: MonetaPaymentProvider) -> None:
    """InvoiceRequest should return a response with transaction ID and CREATED status."""
    txn_id = f"integration-test-{uuid4().hex[:12]}"
    result = await real_provider.create_payment(
        transaction_id=txn_id,
        items=[PaymentItem(name="Integration Test", price=Decimal("1.00"))],
        total_amount=Decimal("1.00"),
        description="Automated integration test — safe to ignore",
        customer_email="test@integration.local",
        return_url="https://example.com/return",
        idempotency_key=f"idem-{uuid4().hex[:8]}",
    )

    assert result.external_id, "external_id (operation ID) must be non-empty"
    assert result.external_id.isdigit(), "operation ID must be numeric string"
    assert "operationId=" in result.payment_url
    assert result.raw_response.get("status") in ("CREATED", "INPROGRESS")


# ------------------------------------------------------------------
# 2. Get operation status for just-created invoice
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_real_get_operation_status(real_provider: MonetaPaymentProvider) -> None:
    """Create an invoice, then query its status via GetOperationDetailsByIdRequest."""
    txn_id = f"integration-status-{uuid4().hex[:12]}"
    created = await real_provider.create_payment(
        transaction_id=txn_id,
        items=[PaymentItem(name="Status Check Test", price=Decimal("1.00"))],
        total_amount=Decimal("1.00"),
        description="Integration test for status check",
        customer_email="test@integration.local",
        return_url="https://example.com/return",
        idempotency_key=f"idem-{uuid4().hex[:8]}",
    )

    status = await real_provider.get_operation_status(created.external_id)

    assert status["id"] == int(created.external_id)
    assert status["status"] in ("CREATED", "INPROGRESS", "SUCCEED", "NOTSTARTED")
    assert "attributes" in status


# ------------------------------------------------------------------
# 3. Fault response on invalid payee account
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_real_fault_on_bad_account(
    real_provider: MonetaPaymentProvider,
) -> None:
    """Sending an invoice to a non-existent payee account should raise ValueError."""
    real_provider._payee_account = "0000000000"

    with pytest.raises(ValueError, match="Moneta API error"):
        await real_provider.create_payment(
            transaction_id=f"fault-test-{uuid4().hex[:12]}",
            items=[PaymentItem(name="Fault Test", price=Decimal("1.00"))],
            total_amount=Decimal("1.00"),
            description="Should fail with fault",
            customer_email="test@integration.local",
            return_url="https://example.com/return",
            idempotency_key=f"idem-{uuid4().hex[:8]}",
        )


# ------------------------------------------------------------------
# 4. Auth error on wrong credentials
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_real_envelope_auth_error(
    real_provider: MonetaPaymentProvider,
) -> None:
    """Wrong username/password should produce a fault, not an HTTP 401."""
    real_provider._username = "invalid-user@nowhere.test"
    real_provider._password = "wrong-password-12345"

    with pytest.raises(ValueError, match="Moneta API error"):
        await real_provider.create_payment(
            transaction_id=f"auth-test-{uuid4().hex[:12]}",
            items=[PaymentItem(name="Auth Test", price=Decimal("1.00"))],
            total_amount=Decimal("1.00"),
            description="Should fail with auth error",
            customer_email="test@integration.local",
            return_url="https://example.com/return",
            idempotency_key=f"idem-{uuid4().hex[:8]}",
        )
