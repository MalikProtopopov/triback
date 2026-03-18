"""Tests for webhook hardening — deduplication, proper status codes, refund handling."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_event,
    create_event_registration,
    create_event_tariff,
    create_payment,
    create_plan,
    create_subscription,
    create_user,
)


@pytest.fixture
def _allow_all_ips(monkeypatch):
    monkeypatch.setattr(
        "app.services.payment_webhook_service.is_ip_allowed", lambda ip: True
    )


async def test_webhook_dedup_returns_ok_on_second_call(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
    _allow_all_ips,
):
    user = await create_user(db_session)
    plan = await create_plan(db_session)
    sub = await create_subscription(
        db_session, user=user, plan=plan, status="pending_payment"
    )
    payment = await create_payment(
        db_session,
        user=user,
        status="pending",
        subscription=sub,
        external_payment_id="ext_123",
    )

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": "ext_123",
            "status": "succeeded",
            "metadata": {"internal_payment_id": str(payment.id)},
        },
    }

    _dedup_store: dict[str, str] = {}

    async def _redis_set(key, value, **kwargs):
        if kwargs.get("nx"):
            if key in _dedup_store:
                return False
            _dedup_store[key] = value
            return True
        _dedup_store[key] = value

    redis_mock.set = AsyncMock(side_effect=_redis_set)

    resp1 = await client.post("/api/v1/webhooks/yookassa", json=payload)
    assert resp1.status_code == 200

    resp2 = await client.post("/api/v1/webhooks/yookassa", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "ok"


async def test_webhook_forbidden_ip_returns_403(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.payment_webhook_service.is_ip_allowed", lambda ip: False
    )

    async def _redis_set_always_true(key, value, **kwargs):
        return True

    redis_mock.set = AsyncMock(side_effect=_redis_set_always_true)

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": "ext_forbidden", "metadata": {}},
    }

    resp = await client.post("/api/v1/webhooks/yookassa", json=payload)
    assert resp.status_code == 403


async def test_refund_decrements_event_seats(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
    admin_user,
    _allow_all_ips,
):

    user = await create_user(db_session)
    event = await create_event(db_session, created_by=admin_user)
    tariff = await create_event_tariff(db_session, event=event, seats_limit=10)
    tariff.seats_taken = 5
    await db_session.flush()

    reg = await create_event_registration(
        db_session, user=user, event=event, tariff=tariff, status="confirmed"
    )
    payment = await create_payment(
        db_session,
        user=user,
        amount=1000.0,
        product_type="event",
        status="succeeded",
        external_payment_id="ext_refund_123",
    )
    payment.event_registration_id = reg.id
    await db_session.flush()

    async def _redis_set_ok(key, value, **kwargs):
        return True

    redis_mock.set = AsyncMock(side_effect=_redis_set_ok)

    payload = {
        "type": "notification",
        "event": "refund.succeeded",
        "object": {"id": "ext_refund_123", "metadata": {}},
    }
    resp = await client.post("/api/v1/webhooks/yookassa", json=payload)
    assert resp.status_code == 200

    await db_session.refresh(tariff)
    assert tariff.seats_taken == 4

    await db_session.refresh(reg)
    assert reg.status == "cancelled"

    await db_session.refresh(payment)
    assert payment.status == "refunded"
