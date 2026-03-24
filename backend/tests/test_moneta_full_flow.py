"""Full-flow tests: payment creation -> Check URL -> Pay URL webhook -> subscription/event activation.

These tests exercise the complete payment lifecycle through real HTTP
endpoints (in-process ASGI) but mock only the external Moneta
``create_payment`` call.  Webhook delivery is simulated with a correct
MD5 signature so the entire internal chain is validated end-to-end.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Plan, Subscription
from app.services.payment_providers.base import CreatePaymentResult
from app.services.payment_providers.moneta_client import _md5

WEBHOOK_SECRET = "flow-test-secret"
MNT_ID = "flow-mnt-id"


def _make_signature(
    mnt_id: str, txn_id: str, op_id: str, amount: str, secret: str,
) -> str:
    return _md5(mnt_id, txn_id, op_id, amount, "RUB", "", "", secret)


# ------------------------------------------------------------------
# Shared fixtures
# ------------------------------------------------------------------


@pytest.fixture
def _moneta_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.PAYMENT_PROVIDER", "moneta")
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", MNT_ID)
    monkeypatch.setattr("app.core.config.settings.MONETA_SUCCESS_URL", "https://test.com/ok")
    monkeypatch.setattr("app.core.config.settings.MONETA_RETURN_URL", "https://test.com/return")


@pytest.fixture
async def sub_plan(db_session: AsyncSession) -> Plan:
    plan = Plan(
        code="annual_flow_test",
        name="Годовая подписка",
        price=15000.00,
        duration_months=12,
        is_active=True,
        plan_type="subscription",
    )
    db_session.add(plan)
    await db_session.flush()
    return plan


@pytest.fixture
async def entry_plan(db_session: AsyncSession) -> Plan:
    plan = Plan(
        code="entry_fee_flow",
        name="Вступительный взнос",
        price=5000.00,
        duration_months=0,
        is_active=True,
        plan_type="entry_fee",
    )
    db_session.add(plan)
    await db_session.flush()
    return plan


@pytest.fixture
async def doctor_profile(db_session: AsyncSession, doctor_user) -> DoctorProfile:
    profile = DoctorProfile(
        user_id=doctor_user.id,
        first_name="Flow",
        last_name="TestDoc",
        phone="+79001112233",
        slug=f"flow-doc-{uuid4().hex[:8]}",
        status="approved",
        has_medical_diploma=True,
    )
    db_session.add(profile)
    await db_session.flush()
    return profile


# ------------------------------------------------------------------
# 1. Full subscription payment flow
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_full_subscription_payment_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
    doctor_profile: DoctorProfile,
    sub_plan: Plan,
    entry_plan: Plan,
    auth_headers_doctor,
    _moneta_settings,
) -> None:
    """End-to-end: pay -> check URL -> pay webhook -> status == active."""
    fake_op_id = "900001"
    mock_result = CreatePaymentResult(
        external_id=fake_op_id,
        payment_url=f"https://test.payanyway.ru/assistant.htm?operationId={fake_op_id}",
    )

    with patch("app.services.subscription_service.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_gp.return_value = mock_provider

        pay_resp = await client.post(
            "/api/v1/subscriptions/pay",
            json={
                "plan_id": str(sub_plan.id),
                "idempotency_key": f"flow-{uuid4().hex[:8]}",
            },
            headers=auth_headers_doctor,
        )

    assert pay_resp.status_code == 201, pay_resp.text
    pay_data = pay_resp.json()
    payment_id = pay_data["payment_id"]
    assert "operationId=" in pay_data["payment_url"]

    total_amount = pay_data["amount"]
    amount_str = f"{total_amount:.2f}"

    # --- Check URL (pre-payment validation) ---
    check_sig = _make_signature(MNT_ID, payment_id, "", amount_str, WEBHOOK_SECRET)
    check_resp = await client.get(
        "/api/v1/webhooks/moneta/check",
        params={
            "MNT_ID": MNT_ID,
            "MNT_TRANSACTION_ID": payment_id,
            "MNT_OPERATION_ID": "",
            "MNT_AMOUNT": amount_str,
            "MNT_CURRENCY_CODE": "RUB",
            "MNT_SUBSCRIBER_ID": "",
            "MNT_TEST_MODE": "",
            "MNT_SIGNATURE": check_sig,
        },
    )
    assert check_resp.status_code == 200
    assert "<MNT_RESULT_CODE>402</MNT_RESULT_CODE>" in check_resp.text

    # --- Pay URL webhook (payment success notification) ---
    pay_sig = _make_signature(MNT_ID, payment_id, fake_op_id, amount_str, WEBHOOK_SECRET)
    webhook_resp = await client.post(
        "/api/v1/webhooks/moneta",
        data={
            "MNT_ID": MNT_ID,
            "MNT_TRANSACTION_ID": payment_id,
            "MNT_OPERATION_ID": fake_op_id,
            "MNT_AMOUNT": amount_str,
            "MNT_CURRENCY_CODE": "RUB",
            "MNT_SUBSCRIBER_ID": "",
            "MNT_TEST_MODE": "",
            "MNT_SIGNATURE": pay_sig,
        },
    )
    assert webhook_resp.status_code == 200
    assert webhook_resp.text == "SUCCESS"

    # --- Verify subscription status via API ---
    with patch("app.services.subscription_service.get_provider") as mock_gp2:
        mock_gp2.return_value = AsyncMock()
        status_resp = await client.get(
            "/api/v1/subscriptions/status",
            headers=auth_headers_doctor,
        )

    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["has_subscription"] is True
    assert status_data["current_subscription"] is not None
    assert status_data["current_subscription"]["status"] == "active"

    # --- Verify DB state ---
    db_payment = (
        await db_session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
    ).scalar_one()
    assert db_payment.status == "succeeded"
    assert db_payment.paid_at is not None
    assert db_payment.moneta_operation_id == fake_op_id


# ------------------------------------------------------------------
# 2. Full event payment flow
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_full_event_payment_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
    _moneta_settings,
) -> None:
    """Simulate event registration payment via webhook -> registration confirmed."""
    from datetime import UTC, datetime

    from app.models.events import Event, EventRegistration, EventTariff

    event = Event(
        title="Flow Test Event",
        slug=f"flow-event-{uuid4().hex[:8]}",
        event_date=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
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

    fake_op_id = "900002"
    payment = Payment(
        user_id=doctor_user.id,
        amount=5000.00,
        product_type="event",
        payment_provider="moneta",
        status="pending",
        event_registration_id=reg.id,
        moneta_operation_id=fake_op_id,
        idempotency_key=f"idem-{uuid4().hex[:8]}",
        description="Event flow test",
    )
    db_session.add(payment)
    await db_session.flush()

    pay_sig = _make_signature(MNT_ID, str(payment.id), fake_op_id, "5000.00", WEBHOOK_SECRET)
    webhook_resp = await client.post(
        "/api/v1/webhooks/moneta",
        data={
            "MNT_ID": MNT_ID,
            "MNT_TRANSACTION_ID": str(payment.id),
            "MNT_OPERATION_ID": fake_op_id,
            "MNT_AMOUNT": "5000.00",
            "MNT_CURRENCY_CODE": "RUB",
            "MNT_SUBSCRIBER_ID": "",
            "MNT_TEST_MODE": "",
            "MNT_SIGNATURE": pay_sig,
        },
    )
    assert webhook_resp.status_code == 200
    assert webhook_resp.text == "SUCCESS"

    await db_session.refresh(reg)
    await db_session.refresh(payment)

    assert payment.status == "succeeded"
    assert payment.paid_at is not None
    assert reg.status == "confirmed"


# ------------------------------------------------------------------
# 3. Check URL — неизвестный платёж → 500 (заказ не актуален)
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_webhook_check_unknown_transaction_returns_500(
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
    sub_plan: Plan,
    _moneta_settings,
) -> None:
    """Неизвестный MNT_TRANSACTION_ID — MNT_RESULT_CODE 500 по семантике Assistant."""
    unknown_txn = str(uuid4())
    sig = _make_signature(MNT_ID, unknown_txn, "", "99999.00", WEBHOOK_SECRET)
    resp = await client.get(
        "/api/v1/webhooks/moneta/check",
        params={
            "MNT_ID": MNT_ID,
            "MNT_TRANSACTION_ID": unknown_txn,
            "MNT_OPERATION_ID": "",
            "MNT_AMOUNT": "99999.00",
            "MNT_CURRENCY_CODE": "RUB",
            "MNT_SUBSCRIBER_ID": "",
            "MNT_TEST_MODE": "",
            "MNT_SIGNATURE": sig,
        },
    )
    assert resp.status_code == 200
    assert "<MNT_RESULT_CODE>500</MNT_RESULT_CODE>" in resp.text


# ------------------------------------------------------------------
# 4. Duplicate webhooks are idempotent
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_duplicate_webhook_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
    sub_plan: Plan,
    _moneta_settings,
) -> None:
    """Two identical Pay URL webhooks should both return SUCCESS; DB updated only once."""
    sub = Subscription(
        user_id=doctor_user.id,
        plan_id=sub_plan.id,
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
        description="Dedup test",
    )
    db_session.add(payment)
    await db_session.flush()

    fake_op_id = "900003"
    sig = _make_signature(MNT_ID, str(payment.id), fake_op_id, "15000.00", WEBHOOK_SECRET)
    params = {
        "MNT_ID": MNT_ID,
        "MNT_TRANSACTION_ID": str(payment.id),
        "MNT_OPERATION_ID": fake_op_id,
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }

    resp1 = await client.post("/api/v1/webhooks/moneta", data=params)
    assert resp1.text == "SUCCESS"

    resp2 = await client.post("/api/v1/webhooks/moneta", data=params)
    assert resp2.text == "SUCCESS"

    await db_session.refresh(payment)
    assert payment.status == "succeeded"
    assert payment.paid_at is not None
