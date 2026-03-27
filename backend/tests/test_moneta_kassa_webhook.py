"""API tests for /api/v1/webhooks/moneta/kassa (kassa Pay URL XML)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscriptions import Payment, Plan, Subscription
from app.services.payment_providers.moneta_client import _md5


def _make_signature(mnt_id: str, txn_id: str, op_id: str, amount: str, secret: str) -> str:
    return _md5(mnt_id, txn_id, op_id, amount, "RUB", "", "", secret)


def _kassa_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.MONETA_KASSA_FISCAL_ENABLED", True)
    monkeypatch.setattr("app.core.config.settings.MONETA_WEBHOOK_SECRET", "kassa-test-secret")
    monkeypatch.setattr("app.core.config.settings.MONETA_MNT_ID", "mnt-kassa")
    monkeypatch.setattr("app.core.config.settings.MONETA_FISCAL_SELLER_INN", "7700000000")
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_FISCAL_SELLER_NAME",
        "ООО Тест",
    )
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_FISCAL_SELLER_PHONE",
        "79000000000",
    )
    monkeypatch.setattr(
        "app.core.config.settings.MONETA_FISCAL_SELLER_ACCOUNT",
        "40800000000000000001",
    )


@pytest.fixture
async def pending_payment_kassa(db_session: AsyncSession, doctor_user) -> Payment:
    plan = Plan(
        code=f"annual_kassa_{uuid4().hex[:6]}",
        name="Kassa Plan",
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
        description="Kassa test",
    )
    db_session.add(payment)
    await db_session.flush()
    return payment


@pytest.mark.anyio
async def test_moneta_kassa_disabled_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/webhooks/moneta/kassa", params={"MNT_ID": "x"})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_moneta_kassa_success_returns_xml(
    client: AsyncClient,
    pending_payment_kassa: Payment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _kassa_env(monkeypatch)

    sig = _make_signature(
        "mnt-kassa",
        str(pending_payment_kassa.id),
        "op-kassa-1",
        "15000.00",
        "kassa-test-secret",
    )
    params = {
        "MNT_ID": "mnt-kassa",
        "MNT_TRANSACTION_ID": str(pending_payment_kassa.id),
        "MNT_OPERATION_ID": "op-kassa-1",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    resp = await client.post("/api/v1/webhooks/moneta/kassa", data=params)
    assert resp.status_code == 200
    assert "application/xml" in resp.headers.get("content-type", "")
    body = resp.text
    assert "<MNT_RESULT_CODE>200</MNT_RESULT_CODE>" in body
    assert "INVENTORY" in body
    assert "CLIENT" in body
    assert "MNT_SIGNATURE" in body


@pytest.mark.anyio
async def test_moneta_kassa_duplicate_still_returns_xml(
    client: AsyncClient,
    pending_payment_kassa: Payment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _kassa_env(monkeypatch)

    sig = _make_signature(
        "mnt-kassa",
        str(pending_payment_kassa.id),
        "op-dup-1",
        "15000.00",
        "kassa-test-secret",
    )
    params = {
        "MNT_ID": "mnt-kassa",
        "MNT_TRANSACTION_ID": str(pending_payment_kassa.id),
        "MNT_OPERATION_ID": "op-dup-1",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": sig,
    }
    r1 = await client.post("/api/v1/webhooks/moneta/kassa", data=params)
    assert r1.status_code == 200
    r2 = await client.post("/api/v1/webhooks/moneta/kassa", data=params)
    assert r2.status_code == 200
    assert "<MNT_RESULT_CODE>200</MNT_RESULT_CODE>" in r2.text


@pytest.mark.anyio
async def test_moneta_kassa_bad_signature_returns_500_xml(
    client: AsyncClient,
    pending_payment_kassa: Payment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _kassa_env(monkeypatch)

    params = {
        "MNT_ID": "mnt-kassa",
        "MNT_TRANSACTION_ID": str(pending_payment_kassa.id),
        "MNT_OPERATION_ID": "op-bad",
        "MNT_AMOUNT": "15000.00",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_SUBSCRIBER_ID": "",
        "MNT_TEST_MODE": "",
        "MNT_SIGNATURE": "deadbeef",
    }
    resp = await client.post("/api/v1/webhooks/moneta/kassa", data=params)
    assert resp.status_code == 200
    assert "<MNT_RESULT_CODE>500</MNT_RESULT_CODE>" in resp.text

