"""Integration tests for Moneta webhook endpoints."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PaymentStatus
from app.models.subscriptions import Payment, Plan, Subscription
from app.services.payment_providers.moneta_client import _md5

RECEIPT_TEST_SECRET = "test-receipt-webhook-secret"


def _make_signature(mnt_id: str, txn_id: str, op_id: str, amount: str, secret: str) -> str:
    return _md5(mnt_id, txn_id, op_id, amount, "RUB", "", "", secret)


def _make_signature_with_command(
    mnt_command: str,
    mnt_id: str,
    txn_id: str,
    op_id: str,
    amount: str,
    secret: str,
) -> str:
    """Signature for MNT_COMMAND format (DEBIT/CREDIT/AUTHORISE/CANCELLED_*)."""
    return _md5(
        mnt_command, mnt_id, txn_id, op_id, amount, "RUB", "", "", secret
    )


@pytest.fixture
async def pending_payment(db_session: AsyncSession, doctor_user) -> Payment:
    plan = Plan(
        code="annual_test",
        name="Test Annual",
        price=15000.00,
        duration_months=12,
        is_active=True,
        plan_type="subscription",
    )
    db_session.add(plan)
    await db_session.flush()

    sub = Subscription(
        user_id=doctor_user.id,
        plan_id=plan.id,
        status="pending_payment",
    )
    db_session.add(sub)
    await db_session.flush()

    payment = Payment(
        user_id=doctor_user.id,
        amount=15000.00,
        product_type="subscription",
        payment_provider="moneta",
        status="pending",
        subscription_id=sub.id,
        idempotency_key=f"idem-{uuid4().hex[:8]}",
        description="Test Annual — Ассоциация трихологов",
    )
    db_session.add(payment)
    await db_session.flush()
    return payment


@pytest.mark.anyio
async def test_moneta_pay_url_success(
    client: AsyncClient,
    pending_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    sig = _make_signature("mnt-1", str(pending_payment.id), "op-123", "15000.00", "test-secret")
    params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(pending_payment.id),
        "MNT_OPERATION_ID": "op-123",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    resp = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp.status_code == 200
    assert resp.text == "SUCCESS"


@pytest.mark.anyio
async def test_moneta_pay_url_with_mnt_command_debit(
    client: AsyncClient,
    pending_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    """Pay URL with MNT_COMMAND=DEBIT uses formula with MNT_OPERATION_ID."""
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    sig = _make_signature_with_command(
        "DEBIT", "mnt-1", str(pending_payment.id), "op-456", "15000.00", "test-secret"
    )
    params = {
        "MNT_COMMAND": "DEBIT",
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(pending_payment.id),
        "MNT_OPERATION_ID": "op-456",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    resp = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp.status_code == 200
    assert resp.text == "SUCCESS"


@pytest.mark.anyio
async def test_moneta_pay_url_cancelled_debit_returns_success(
    client: AsyncClient,
    db_session: AsyncSession,
    pending_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    """CANCELLED_DEBIT returns SUCCESS and cancels the payment (so user can re-register)."""
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    sig = _make_signature_with_command(
        "CANCELLED_DEBIT", "mnt-1", str(pending_payment.id), "op-789", "15000.00", "test-secret"
    )
    params = {
        "MNT_COMMAND": "CANCELLED_DEBIT",
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(pending_payment.id),
        "MNT_OPERATION_ID": "op-789",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    resp = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp.status_code == 200
    assert resp.text == "SUCCESS"
    await db_session.refresh(pending_payment)
    assert pending_payment.status == "failed"


@pytest.mark.anyio
async def test_moneta_pay_url_invalid_signature(
    client: AsyncClient,
    pending_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(pending_payment.id),
        "MNT_OPERATION_ID": "op-123",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": "invalid-sig",
    }
    resp = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp.status_code == 200
    assert resp.text == "FAIL"


@pytest.mark.anyio
async def test_moneta_pay_url_dedup(
    client: AsyncClient,
    pending_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    sig = _make_signature("mnt-1", str(pending_payment.id), "op-dedup", "15000.00", "test-secret")
    params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(pending_payment.id),
        "MNT_OPERATION_ID": "op-dedup",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    resp1 = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp1.text == "SUCCESS"

    resp2 = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp2.text == "SUCCESS"


@pytest.mark.anyio
async def test_moneta_check_url_valid_order(
    client: AsyncClient,
    pending_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    txn_id = str(pending_payment.id)
    sig = _make_signature("mnt-1", txn_id, "", "15000.00", "test-secret")
    params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": txn_id,
        "MNT_OPERATION_ID": "",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    resp = await client.get("/api/v1/webhooks/moneta/check", params=params)
    assert resp.status_code == 200
    assert "<MNT_RESULT_CODE>200</MNT_RESULT_CODE>" in resp.text


@pytest.mark.anyio
async def test_moneta_check_url_unknown_order(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    unknown_txn = str(uuid4())
    sig = _make_signature("mnt-1", unknown_txn, "", "", "test-secret")
    params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": unknown_txn,
        "MNT_OPERATION_ID": "",
        "MNT_AMOUNT": "",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    resp = await client.get("/api/v1/webhooks/moneta/check", params=params)
    assert resp.status_code == 200
    assert "<MNT_RESULT_CODE>402</MNT_RESULT_CODE>" in resp.text


@pytest.mark.anyio
async def test_moneta_receipt_webhook(
    client: AsyncClient,
    pending_payment: Payment,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_RECEIPT_WEBHOOK_SECRET",
        RECEIPT_TEST_SECRET,
    )
    pending_payment.moneta_operation_id = "receipt-op-1"
    pending_payment.status = PaymentStatus.SUCCEEDED
    await db_session.flush()

    body = {
        "operation": "receipt-op-1",
        "receipt": "https://receipt.example.com/12345",
    }
    resp = await client.post(
        "/api/v1/webhooks/moneta/receipt",
        json=body,
        headers={"X-Moneta-Receipt-Secret": RECEIPT_TEST_SECRET},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_moneta_receipt_webhook_unknown_operation(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_RECEIPT_WEBHOOK_SECRET",
        RECEIPT_TEST_SECRET,
    )
    body = {
        "operation": "unknown-op",
        "receipt": "https://receipt.example.com/99",
    }
    resp = await client.post(
        "/api/v1/webhooks/moneta/receipt",
        json=body,
        headers={"X-Moneta-Receipt-Secret": RECEIPT_TEST_SECRET},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_moneta_receipt_webhook_forbidden_without_auth(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.settings.DEBUG", False)
    monkeypatch.setattr("app.core.config.settings.MONETA_RECEIPT_WEBHOOK_SECRET", "")
    monkeypatch.setattr("app.core.config.settings.MONETA_RECEIPT_IP_ALLOWLIST", "")
    monkeypatch.setattr("app.services.payment_utils._MONETA_RECEIPT_NETWORKS", [])

    body = {"operation": "any", "receipt": "https://receipt.example.com/x"}
    resp = await client.post("/api/v1/webhooks/moneta/receipt", json=body)
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.anyio
async def test_moneta_invalid_signature_releases_dedup_key(
    client: AsyncClient,
    pending_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    """Invalid Moneta signature must not permanently consume the Redis dedup slot.

    Regression test for the critical defect where ``SET NX`` ran *before*
    ``verify_webhook``, and a failed signature verification did not clean up
    the dedup key, blocking all subsequent legitimate retries for the same
    ``MNT_OPERATION_ID``.
    """
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    op_id = f"op-dedup-{uuid4().hex[:8]}"
    base_params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(pending_payment.id),
        "MNT_OPERATION_ID": op_id,
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
    }

    # First call: bad signature → FAIL; dedup key must be released.
    resp_bad = await client.get(
        "/api/v1/webhooks/moneta",
        params={**base_params, "MNT_SIGNATURE": "bad-sig"},
    )
    assert resp_bad.status_code == 200
    assert resp_bad.text == "FAIL"

    # Second call: same op_id, now valid signature → must be processed (not short-circuited by dedup).
    good_sig = _make_signature("mnt-1", str(pending_payment.id), op_id, "15000.00", "test-secret")
    resp_good = await client.get(
        "/api/v1/webhooks/moneta",
        params={**base_params, "MNT_SIGNATURE": good_sig},
    )
    assert resp_good.status_code == 200
    assert resp_good.text == "SUCCESS"


@pytest.mark.anyio
async def test_moneta_check_url_invalid_signature(
    client: AsyncClient,
    pending_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(pending_payment.id),
        "MNT_OPERATION_ID": "",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": "bad-sig",
    }
    resp = await client.get("/api/v1/webhooks/moneta/check", params=params)
    assert resp.status_code == 200
    assert "<MNT_RESULT_CODE>500</MNT_RESULT_CODE>" in resp.text


@pytest.mark.anyio
async def test_yookassa_webhook_still_works(client: AsyncClient):
    """Ensure YooKassa webhook endpoint is not broken."""
    body = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": "nonexistent-id", "status": "succeeded"},
    }
    resp = await client.post("/api/v1/webhooks/yookassa", json=body)
    assert resp.status_code in (200, 403)


# ------------------------------------------------------------------
# Test #14: handle_moneta_payment_succeeded activates subscription
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_pay_url_activates_subscription(
    db_session: AsyncSession,
    doctor_user,
):
    """Moneta webhook processing should activate subscription and set dates."""
    from app.services.payment_webhook_service import PaymentWebhookService

    plan = Plan(
        code="annual_activation_test",
        name="Activation Test",
        price=15000.00,
        duration_months=12,
        is_active=True,
        plan_type="subscription",
    )
    db_session.add(plan)
    await db_session.flush()

    sub = Subscription(
        user_id=doctor_user.id,
        plan_id=plan.id,
        status="pending_payment",
    )
    db_session.add(sub)
    await db_session.flush()

    payment = Payment(
        user_id=doctor_user.id,
        amount=15000.00,
        product_type="subscription",
        payment_provider="moneta",
        status="pending",
        subscription_id=sub.id,
        moneta_operation_id="op-activation",
        idempotency_key=f"idem-{uuid4().hex[:8]}",
        description="Activation test",
    )
    db_session.add(payment)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    await svc.handle_moneta_payment_succeeded(payment)

    await db_session.refresh(sub)
    await db_session.refresh(payment)

    assert payment.status == "succeeded"
    assert payment.paid_at is not None
    assert sub.status == "active"
    assert sub.starts_at is not None
    assert sub.ends_at is not None
    assert sub.ends_at > sub.starts_at


# ------------------------------------------------------------------
# Test #14: handle_moneta_payment_succeeded confirms event registration
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_pay_url_confirms_event_registration(
    db_session: AsyncSession,
    doctor_user,
):
    """Moneta webhook processing should confirm event registration."""
    from datetime import UTC, datetime

    from app.models.events import Event, EventRegistration, EventTariff
    from app.services.payment_webhook_service import PaymentWebhookService

    event = Event(
        title="Test Event",
        slug=f"test-event-{uuid4().hex[:8]}",
        event_date=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        status="upcoming",
        created_by=doctor_user.id,
    )
    db_session.add(event)
    await db_session.flush()

    tariff = EventTariff(
        event_id=event.id,
        name="Standard",
        price=5000.00,
        member_price=3000.00,
        is_active=True,
    )
    db_session.add(tariff)
    await db_session.flush()

    reg = EventRegistration(
        user_id=doctor_user.id,
        event_id=event.id,
        event_tariff_id=tariff.id,
        applied_price=5000.00,
        status="pending",
    )
    db_session.add(reg)
    await db_session.flush()

    payment = Payment(
        user_id=doctor_user.id,
        amount=5000.00,
        product_type="event",
        payment_provider="moneta",
        status="pending",
        event_registration_id=reg.id,
        moneta_operation_id="op-event-confirm",
        idempotency_key=f"idem-{uuid4().hex[:8]}",
        description="Event registration test",
    )
    db_session.add(payment)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    await svc.handle_moneta_payment_succeeded(payment)

    await db_session.refresh(reg)
    await db_session.refresh(payment)

    assert payment.status == "succeeded"
    assert payment.paid_at is not None
    assert reg.status == "confirmed"
