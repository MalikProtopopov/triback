"""Tests for event registration flow."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


async def test_register_for_event_authenticated(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await db_session.commit()

    mock_resp = {
        "id": "yoo_evt_" + uuid4().hex[:8],
        "status": "pending",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/evt"},
    }

    with patch(
        "app.services.event_registration_service.YooKassaClient.create_payment",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = await client.post(
            f"/api/v1/events/{event.id}/register",
            headers=auth_headers_doctor,
            json={"tariff_id": str(tariff.id), "idempotency_key": uuid4().hex},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["payment_url"] is not None
    assert data["applied_price"] == 2000.0
    assert data["is_member_price"] is False


async def test_register_member_gets_discount(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_event,
        create_event_tariff,
        create_plan,
        create_subscription,
        create_user,
    )

    admin = await create_user(db_session, email="evt_admin2@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    plan = await create_plan(db_session)
    await create_subscription(db_session, user=doctor_user, plan=plan, status="active")
    await db_session.commit()

    mock_resp = {
        "id": "yoo_mbr_" + uuid4().hex[:8],
        "status": "pending",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/mbr"},
    }

    with patch(
        "app.services.event_registration_service.YooKassaClient.create_payment",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = await client.post(
            f"/api/v1/events/{event.id}/register",
            headers=auth_headers_doctor,
            json={"tariff_id": str(tariff.id), "idempotency_key": uuid4().hex},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["applied_price"] == 1000.0
    assert data["is_member_price"] is True


async def test_register_seat_limit(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin3@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(
        db_session, event=event, price=1000, member_price=500, seats_limit=1
    )
    tariff.seats_taken = 1
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/events/{event.id}/register",
        headers=auth_headers_doctor,
        json={"tariff_id": str(tariff.id), "idempotency_key": uuid4().hex},
    )
    assert resp.status_code == 422


async def test_register_guest_flow(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin4@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)


    from tests.factories import create_role

    await create_role(db_session, name="user", title="User")
    await db_session.commit()

    mock_resp = {
        "id": "yoo_guest_" + uuid4().hex[:8],
        "status": "pending",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/guest"},
    }

    with patch(
        "app.services.event_registration_service.YooKassaClient.create_payment",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = await client.post(
            f"/api/v1/events/{event.id}/register",
            json={
                "tariff_id": str(tariff.id),
                "idempotency_key": uuid4().hex,
                "guest_full_name": "Guest User",
                "guest_email": f"guest_{uuid4().hex[:6]}@test.com",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["applied_price"] == 2000.0
    assert data["is_member_price"] is False


async def test_register_event_not_found(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin5@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/events/{uuid4()}/register",
        headers=auth_headers_doctor,
        json={"tariff_id": str(tariff.id), "idempotency_key": uuid4().hex},
    )
    assert resp.status_code == 404


async def test_register_closed_event(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin6@test.com")
    event = await create_event(db_session, created_by=admin, status="finished")
    tariff = await create_event_tariff(db_session, event=event)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/events/{event.id}/register",
        headers=auth_headers_doctor,
        json={"tariff_id": str(tariff.id), "idempotency_key": uuid4().hex},
    )
    assert resp.status_code == 422


async def test_webhook_event_payment_succeeded(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from app.models.subscriptions import Payment
    from tests.factories import (
        create_event,
        create_event_registration,
        create_event_tariff,
        create_user,
    )

    user = await create_user(db_session, email="wh_event@test.com")
    admin = await create_user(db_session, email="wh_admin@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event)
    reg = await create_event_registration(
        db_session, user=user, event=event, tariff=tariff, status="pending"
    )

    payment = Payment(
        user_id=user.id,
        amount=1000.0,
        product_type="event",
        payment_provider="yookassa",
        status="pending",
        event_registration_id=reg.id,
        external_payment_id="yoo_evt_wh",
    )
    db_session.add(payment)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": "yoo_evt_wh",
                "status": "succeeded",
                "amount": {"value": "1000.00", "currency": "RUB"},
                "metadata": {"internal_payment_id": str(payment.id), "product_type": "event"},
            },
        },
        headers={"x-forwarded-for": "185.71.76.1"},
    )
    assert resp.status_code == 200
