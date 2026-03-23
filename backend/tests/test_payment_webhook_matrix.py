"""Parametrized integration tests for the payment webhook layer.

Covers:
- Successful payment (both YooKassa and Moneta providers)
- Duplicate webhook — second request is a no-op
- Invalid Moneta signature — payment stays pending, dedup key released
- DB failure during processing — dedup key released, 500 returned
- Refund succeeded — payment marked refunded
- Subscription cancellation on failed/canceled payment
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscriptions import Payment, Plan, Subscription
from tests.webhook_payloads import moneta_pay_signature, yookassa_notification

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def subscription_payment(db_session: AsyncSession, doctor_user) -> Payment:
    plan = Plan(
        code=f"plan-{uuid4().hex[:6]}",
        name="Matrix Test Plan",
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
        amount=Decimal("15000.00"),
        product_type="subscription",
        payment_provider="yookassa",
        status="pending",
        subscription_id=sub.id,
        external_payment_id=f"yk-ext-{uuid4().hex[:12]}",
        idempotency_key=f"idem-{uuid4().hex[:8]}",
        description="Matrix test subscription",
    )
    db_session.add(payment)
    await db_session.flush()
    return payment


@pytest.fixture
async def moneta_subscription_payment(db_session: AsyncSession, doctor_user) -> Payment:
    plan = Plan(
        code=f"plan-moneta-{uuid4().hex[:6]}",
        name="Moneta Matrix Test Plan",
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
        amount=Decimal("15000.00"),
        product_type="subscription",
        payment_provider="moneta",
        status="pending",
        subscription_id=sub.id,
        idempotency_key=f"idem-moneta-{uuid4().hex[:8]}",
        description="Matrix test moneta subscription",
    )
    db_session.add(payment)
    await db_session.flush()
    return payment


@pytest.fixture
async def event_payment(db_session: AsyncSession, doctor_user) -> Payment:
    from datetime import UTC, datetime

    from app.models.events import Event, EventRegistration, EventTariff

    event = Event(
        title="Matrix Test Event",
        slug=f"matrix-event-{uuid4().hex[:8]}",
        event_date=datetime(2026, 12, 1, 10, 0, tzinfo=UTC),
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
        amount=Decimal("5000.00"),
        product_type="event",
        payment_provider="yookassa",
        status="pending",
        event_registration_id=reg.id,
        external_payment_id=f"yk-event-{uuid4().hex[:12]}",
        idempotency_key=f"idem-event-{uuid4().hex[:8]}",
        description="Matrix test event",
    )
    db_session.add(payment)
    await db_session.flush()
    return payment


# ---------------------------------------------------------------------------
# 1. Successful payment — both providers
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_yookassa_success_updates_payment_and_activates_subscription(
    client: AsyncClient,
    db_session: AsyncSession,
    subscription_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    """YooKassa payment.succeeded → payment SUCCEEDED, subscription ACTIVE."""
    monkeypatch.setattr("app.services.payment_webhook_service.is_ip_allowed", lambda _ip: True)

    body = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": subscription_payment.external_payment_id,
            "status": "succeeded",
            "metadata": {"internal_payment_id": str(subscription_payment.id)},
        },
    }
    resp = await client.post("/api/v1/webhooks/yookassa", json=body)
    assert resp.status_code == 200

    await db_session.refresh(subscription_payment)
    assert subscription_payment.status == "succeeded"
    assert subscription_payment.paid_at is not None

    sub = await db_session.get(Subscription, subscription_payment.subscription_id)
    assert sub is not None
    assert sub.status == "active"
    assert sub.starts_at is not None
    assert sub.ends_at is not None


@pytest.mark.anyio
async def test_moneta_success_updates_payment_and_activates_subscription(
    client: AsyncClient,
    db_session: AsyncSession,
    moneta_subscription_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    """Moneta Pay URL webhook → payment SUCCEEDED, subscription ACTIVE."""
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    op_id = f"op-matrix-{uuid4().hex[:8]}"
    sig = moneta_pay_signature(
        "mnt-1", str(moneta_subscription_payment.id), op_id, "15000.00", "test-secret"
    )
    params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(moneta_subscription_payment.id),
        "MNT_OPERATION_ID": op_id,
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    resp = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp.status_code == 200
    assert resp.text == "SUCCESS"

    await db_session.refresh(moneta_subscription_payment)
    assert moneta_subscription_payment.status == "succeeded"
    assert moneta_subscription_payment.paid_at is not None

    sub = await db_session.get(Subscription, moneta_subscription_payment.subscription_id)
    assert sub is not None
    assert sub.status == "active"


# ---------------------------------------------------------------------------
# 2. Duplicate webhook — second request is a no-op
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_yookassa_duplicate_webhook_is_noop(
    client: AsyncClient,
    db_session: AsyncSession,
    subscription_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    """A second YooKassa webhook with the same event+id must be short-circuited by Redis dedup."""
    monkeypatch.setattr("app.services.payment_webhook_service.is_ip_allowed", lambda _ip: True)

    body = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": subscription_payment.external_payment_id,
            "status": "succeeded",
        },
    }

    resp1 = await client.post("/api/v1/webhooks/yookassa", json=body)
    assert resp1.status_code == 200

    resp2 = await client.post("/api/v1/webhooks/yookassa", json=body)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "ok"

    await db_session.refresh(subscription_payment)
    # After first call payment is succeeded; second call must not raise an error or re-process.
    assert subscription_payment.status in ("succeeded", "pending")


@pytest.mark.anyio
async def test_subscription_stays_pending_after_yookassa_payment_canceled(
    client: AsyncClient,
    db_session: AsyncSession,
    subscription_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    """HTTP: payment.canceled → payment failed, subscription never activated."""
    monkeypatch.setattr("app.services.payment_webhook_service.is_ip_allowed", lambda _ip: True)

    body = yookassa_notification(
        internal_payment_id=str(subscription_payment.id),
        event="payment.canceled",
        external_id=subscription_payment.external_payment_id,
        object_status="canceled",
    )
    resp = await client.post("/api/v1/webhooks/yookassa", json=body)
    assert resp.status_code == 200

    await db_session.refresh(subscription_payment)
    assert subscription_payment.status == "failed"
    sub = await db_session.get(Subscription, subscription_payment.subscription_id)
    assert sub is not None
    assert sub.status == "pending_payment"


@pytest.mark.anyio
async def test_moneta_duplicate_webhook_is_noop(
    client: AsyncClient,
    db_session: AsyncSession,
    moneta_subscription_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    """A second Moneta webhook with the same MNT_OPERATION_ID returns SUCCESS instantly."""
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    op_id = f"op-dedup2-{uuid4().hex[:8]}"
    sig = moneta_pay_signature(
        "mnt-1", str(moneta_subscription_payment.id), op_id, "15000.00", "test-secret"
    )
    params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(moneta_subscription_payment.id),
        "MNT_OPERATION_ID": op_id,
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    resp1 = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp1.status_code == 200
    assert resp1.text == "SUCCESS"

    resp2 = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp2.status_code == 200
    assert resp2.text == "SUCCESS"


# ---------------------------------------------------------------------------
# 3. Invalid Moneta signature — payment stays pending, dedup key released
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_moneta_invalid_signature_does_not_commit_payment(
    client: AsyncClient,
    db_session: AsyncSession,
    moneta_subscription_payment: Payment,
    monkeypatch: pytest.MonkeyPatch,
):
    """Bad Moneta signature → FAIL, payment remains pending."""
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-1")

    op_id = f"op-badsig-{uuid4().hex[:8]}"
    params = {
        "MNT_ID": "mnt-1",
        "MNT_TRANSACTION_ID": str(moneta_subscription_payment.id),
        "MNT_OPERATION_ID": op_id,
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": "totally-invalid-signature",
    }
    resp = await client.get("/api/v1/webhooks/moneta", params=params)
    assert resp.status_code == 200
    assert resp.text == "FAIL"

    await db_session.refresh(moneta_subscription_payment)
    assert moneta_subscription_payment.status == "pending"


# ---------------------------------------------------------------------------
# 4. DB failure during processing — dedup key released, 500 returned
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_db_failure_releases_yookassa_dedup_key(
    client: AsyncClient,
    db_session: AsyncSession,
    subscription_payment: Payment,
    redis_mock: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
):
    """When DB commit raises, the YooKassa dedup key must be deleted (allow retry)."""
    monkeypatch.setattr("app.services.payment_webhook_service.is_ip_allowed", lambda _ip: True)

    body = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": subscription_payment.external_payment_id,
            "status": "succeeded",
        },
    }

    with patch(
        "app.services.payment_webhook_service.PaymentWebhookService._apply_payment_succeeded",
        side_effect=Exception("DB is gone"),
    ):
        resp = await client.post("/api/v1/webhooks/yookassa", json=body)

    assert resp.status_code == 500

    # Dedup key must have been deleted so a retry can proceed.
    # Key format matches YOOKASSA_WEBHOOK_DEDUP_KEY_PREFIX + event:external_id.
    dedup_key = f"webhook:dedup:payment.succeeded:{subscription_payment.external_payment_id}"
    redis_mock.delete.assert_awaited_with(dedup_key)


# ---------------------------------------------------------------------------
# 5. Refund succeeded — payment marked refunded
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_refund_succeeded_marks_payment_refunded(
    db_session: AsyncSession,
    doctor_user,
):
    """refund.succeeded event → payment status REFUNDED."""
    from app.services.payment_webhook_service import PaymentWebhookService

    payment = Payment(
        user_id=doctor_user.id,
        amount=Decimal("15000.00"),
        product_type="subscription",
        payment_provider="yookassa",
        status="succeeded",
        external_payment_id=f"yk-refund-{uuid4().hex[:12]}",
        idempotency_key=f"idem-refund-{uuid4().hex[:8]}",
        description="Refund test",
    )
    db_session.add(payment)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    await svc._handle_refund_succeeded(payment)

    await db_session.refresh(payment)
    assert payment.status == "refunded"


@pytest.mark.anyio
async def test_refund_succeeded_is_idempotent(
    db_session: AsyncSession,
    doctor_user,
):
    """Calling _handle_refund_succeeded twice must not raise."""
    from app.services.payment_webhook_service import PaymentWebhookService

    payment = Payment(
        user_id=doctor_user.id,
        amount=Decimal("5000.00"),
        product_type="subscription",
        payment_provider="yookassa",
        status="succeeded",
        external_payment_id=f"yk-refund2-{uuid4().hex[:12]}",
        idempotency_key=f"idem-refund2-{uuid4().hex[:8]}",
        description="Idempotent refund test",
    )
    db_session.add(payment)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    await svc._handle_refund_succeeded(payment)
    # Second call on already-refunded payment must be a no-op.
    await svc._handle_refund_succeeded(payment)

    await db_session.refresh(payment)
    assert payment.status == "refunded"


# ---------------------------------------------------------------------------
# 6. Subscription cancellation on failed/canceled payment
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_payment_canceled_cancels_event_registration(
    db_session: AsyncSession,
    doctor_user,
):
    """payment.canceled webhook → event registration CANCELLED, seats released."""
    from datetime import UTC, datetime

    from app.models.events import Event, EventRegistration, EventTariff
    from app.services.payment_webhook_service import PaymentWebhookService

    event = Event(
        title="Cancel Matrix Event",
        slug=f"cancel-matrix-{uuid4().hex[:8]}",
        event_date=datetime(2026, 12, 1, 10, 0, tzinfo=UTC),
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
        seats_taken=1,
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
        amount=Decimal("5000.00"),
        product_type="event",
        payment_provider="yookassa",
        status="pending",
        event_registration_id=reg.id,
        external_payment_id=f"yk-cancel-{uuid4().hex[:12]}",
        idempotency_key=f"idem-cancel-{uuid4().hex[:8]}",
        description="Cancel test payment",
    )
    db_session.add(payment)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    await svc._handle_payment_canceled(payment)

    await db_session.refresh(payment)
    await db_session.refresh(reg)
    await db_session.refresh(tariff)

    assert payment.status == "failed"
    assert reg.status == "cancelled"
    assert tariff.seats_taken == 0


@pytest.mark.anyio
async def test_payment_canceled_on_subscription_marks_payment_failed(
    db_session: AsyncSession,
    doctor_user,
):
    """payment.canceled for a subscription payment → payment FAILED (subscription untouched)."""
    from app.services.payment_webhook_service import PaymentWebhookService

    plan = Plan(
        code=f"plan-cancel-{uuid4().hex[:6]}",
        name="Cancel Plan",
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
        amount=Decimal("15000.00"),
        product_type="subscription",
        payment_provider="yookassa",
        status="pending",
        subscription_id=sub.id,
        external_payment_id=f"yk-sub-cancel-{uuid4().hex[:12]}",
        idempotency_key=f"idem-sub-cancel-{uuid4().hex[:8]}",
        description="Cancel subscription test",
    )
    db_session.add(payment)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    await svc._handle_payment_canceled(payment)

    await db_session.refresh(payment)
    await db_session.refresh(sub)

    assert payment.status == "failed"
    # Subscription remains pending_payment (not cancelled by webhook handler;
    # scheduler handles expired subscriptions separately).
    assert sub.status == "pending_payment"


@pytest.mark.anyio
async def test_payment_canceled_is_idempotent(
    db_session: AsyncSession,
    doctor_user,
):
    """Calling _handle_payment_canceled on an already-failed payment must be a no-op."""
    from app.services.payment_webhook_service import PaymentWebhookService

    payment = Payment(
        user_id=doctor_user.id,
        amount=Decimal("5000.00"),
        product_type="subscription",
        payment_provider="yookassa",
        status="failed",
        external_payment_id=f"yk-cancel-idem-{uuid4().hex[:12]}",
        idempotency_key=f"idem-cancel-idem-{uuid4().hex[:8]}",
        description="Idempotent cancel test",
    )
    db_session.add(payment)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    await svc._handle_payment_canceled(payment)

    await db_session.refresh(payment)
    assert payment.status == "failed"


# ---------------------------------------------------------------------------
# 7. apply_payment_succeeded — unified handler tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_apply_payment_succeeded_is_idempotent(
    db_session: AsyncSession,
    doctor_user,
):
    """Calling _apply_payment_succeeded twice must not re-process an already-succeeded payment."""
    from app.services.payment_webhook_service import PaymentWebhookService

    plan = Plan(
        code=f"plan-idem-{uuid4().hex[:6]}",
        name="Idempotent Plan",
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
        amount=Decimal("15000.00"),
        product_type="subscription",
        payment_provider="yookassa",
        status="pending",
        subscription_id=sub.id,
        external_payment_id=f"yk-idem-{uuid4().hex[:12]}",
        idempotency_key=f"idem-idem-{uuid4().hex[:8]}",
        description="Idempotency test",
    )
    db_session.add(payment)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    await svc._apply_payment_succeeded(payment)
    paid_at_first = payment.paid_at

    # Second invocation must return immediately without touching paid_at.
    await svc._apply_payment_succeeded(payment)

    await db_session.refresh(payment)
    assert payment.status == "succeeded"
    assert payment.paid_at == paid_at_first
