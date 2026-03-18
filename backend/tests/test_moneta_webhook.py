"""Integration tests for Moneta webhook endpoints."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscriptions import Payment, Plan, Subscription
from app.services.payment_providers.moneta_client import _md5


def _make_signature(mnt_id: str, txn_id: str, op_id: str, amount: str, secret: str) -> str:
    return _md5(mnt_id, txn_id, op_id, amount, "RUB", "", "", secret)


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
    pending_payment.moneta_operation_id = "receipt-op-1"
    pending_payment.status = "succeeded"  # type: ignore[assignment]
    await db_session.flush()

    body = {
        "operation": "receipt-op-1",
        "receipt": "https://receipt.example.com/12345",
    }
    resp = await client.post("/api/v1/webhooks/moneta/receipt", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_moneta_receipt_webhook_unknown_operation(
    client: AsyncClient,
):
    body = {
        "operation": "unknown-op",
        "receipt": "https://receipt.example.com/99",
    }
    resp = await client.post("/api/v1/webhooks/moneta/receipt", json=body)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


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
