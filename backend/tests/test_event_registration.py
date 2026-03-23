"""Tests for event registration flow (3-scenario guest verification)."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.events import EventTariff
from app.models.users import User
from app.services.payment_providers.base import CreatePaymentResult

# ── Scenario 1: Authenticated user -> direct payment ──────────────


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

    mock_result = CreatePaymentResult(
        external_id="op_evt_" + uuid4().hex[:8],
        payment_url="https://moneta.test/pay/evt",
    )

    with patch("app.services.event_registration_service.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_gp.return_value = mock_provider

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
    assert data["action"] is None


async def test_register_with_x_access_token_header(
    client: AsyncClient,
    doctor_user: User,
    db_session: AsyncSession,
):
    """X-Access-Token header works as fallback when Authorization is not sent."""
    from app.core.security import create_access_token
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_xt@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await db_session.commit()

    token = create_access_token(doctor_user.id, "doctor")
    headers = {"X-Access-Token": token}

    mock_result = CreatePaymentResult(
        external_id="op_xt_" + uuid4().hex[:8],
        payment_url="https://moneta.test/pay/xt",
    )

    with patch("app.services.event_registration_service.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_gp.return_value = mock_provider

        resp = await client.post(
            f"/api/v1/events/{event.id}/register",
            headers=headers,
            json={"tariff_id": str(tariff.id), "idempotency_key": uuid4().hex},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["payment_url"] is not None
    assert data["action"] is None


async def test_register_with_access_token_cookie(
    client: AsyncClient,
    doctor_user: User,
    db_session: AsyncSession,
):
    """access_token cookie works as fallback when Authorization is not sent."""
    from app.core.security import create_access_token
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_cookie@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await db_session.commit()

    token = create_access_token(doctor_user.id, "doctor")
    cookies = {"access_token": token}

    mock_result = CreatePaymentResult(
        external_id="op_ck_" + uuid4().hex[:8],
        payment_url="https://moneta.test/pay/ck",
    )

    with patch("app.services.event_registration_service.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_gp.return_value = mock_provider

        resp = await client.post(
            f"/api/v1/events/{event.id}/register",
            cookies=cookies,
            json={"tariff_id": str(tariff.id), "idempotency_key": uuid4().hex},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["payment_url"] is not None
    assert data["action"] is None


async def test_register_member_gets_discount(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_doctor_profile,
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
    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await create_subscription(db_session, user=doctor_user, plan=plan, status="active")
    await db_session.commit()

    mock_result = CreatePaymentResult(
        external_id="op_mbr_" + uuid4().hex[:8],
        payment_url="https://moneta.test/pay/mbr",
    )

    with patch("app.services.event_registration_service.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_gp.return_value = mock_provider

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


# ── Scenario 2: Unauthenticated, email exists -> verify_existing ──


async def test_register_guest_existing_email(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_ex@test.com")
    existing = await create_user(db_session, email="existing_guest@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/events/{event.id}/register",
        json={
            "tariff_id": str(tariff.id),
            "idempotency_key": uuid4().hex,
            "guest_email": existing.email,
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["action"] == "verify_existing"
    assert data["masked_email"] == "e***@test.com"
    assert data["registration_id"] is None
    assert data["payment_url"] is None


# ── Scenario 3: Unauthenticated, new email -> verify_new_email ────


async def test_register_guest_new_email_sends_code(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_new@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await db_session.commit()

    guest_email = f"newguest_{uuid4().hex[:6]}@test.com"

    with patch(
        "app.tasks.email_tasks.send_event_verification_code",
    ) as mock_task:
        mock_task.kiq = AsyncMock()
        resp = await client.post(
            f"/api/v1/events/{event.id}/register",
            json={
                "tariff_id": str(tariff.id),
                "idempotency_key": uuid4().hex,
                "guest_email": guest_email,
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["action"] == "verify_new_email"
    assert data["masked_email"] is not None
    assert data["registration_id"] is None

    redis_mock.set.assert_called()
    stored_call = redis_mock.set.call_args
    assert f"event_reg_verify:{guest_email}" == stored_call[0][0]


async def test_confirm_guest_registration_success(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
):
    from tests.factories import create_event, create_event_tariff, create_role, create_user

    admin = await create_user(db_session, email="evt_admin_confirm@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await create_role(db_session, name="user", title="User")
    await db_session.commit()

    guest_email = f"confirm_{uuid4().hex[:6]}@test.com"
    code = "123456"

    await redis_mock.set(
        f"event_reg_verify:{guest_email}",
        json.dumps({
            "code": code,
            "event_id": str(event.id),
            "tariff_id": str(tariff.id),
        }),
    )

    mock_result = CreatePaymentResult(
        external_id="op_confirm_" + uuid4().hex[:8],
        payment_url="https://moneta.test/pay/confirm",
    )

    with (
        patch("app.services.event_registration_service.get_provider") as mock_gp,
        patch(
            "app.tasks.email_tasks.send_guest_account_created",
        ) as mock_email,
    ):
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_gp.return_value = mock_provider
        mock_email.kiq = AsyncMock()
        resp = await client.post(
            f"/api/v1/events/{event.id}/confirm-guest-registration",
            json={
                "email": guest_email,
                "code": code,
                "tariff_id": str(tariff.id),
                "idempotency_key": uuid4().hex,
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["registration_id"] is not None
    assert data["payment_url"] == "https://moneta.test/pay/confirm"
    assert data["applied_price"] == 2000.0
    assert data["is_member_price"] is False


# ── Invalid code ─────────────────────────────────────────────────


async def test_confirm_guest_registration_invalid_code(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_inv@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await db_session.commit()

    guest_email = f"invalid_{uuid4().hex[:6]}@test.com"

    await redis_mock.set(
        f"event_reg_verify:{guest_email}",
        json.dumps({
            "code": "123456",
            "event_id": str(event.id),
            "tariff_id": str(tariff.id),
        }),
    )

    resp = await client.post(
        f"/api/v1/events/{event.id}/confirm-guest-registration",
        json={
            "email": guest_email,
            "code": "999999",
            "tariff_id": str(tariff.id),
            "idempotency_key": uuid4().hex,
        },
    )

    assert resp.status_code == 422
    assert "Invalid verification code" in resp.json()["error"]["message"]


async def test_confirm_guest_registration_expired_code(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_exp@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await db_session.commit()

    guest_email = f"expired_{uuid4().hex[:6]}@test.com"

    resp = await client.post(
        f"/api/v1/events/{event.id}/confirm-guest-registration",
        json={
            "email": guest_email,
            "code": "123456",
            "tariff_id": str(tariff.id),
            "idempotency_key": uuid4().hex,
        },
    )

    assert resp.status_code == 422
    assert "expired" in resp.json()["error"]["message"].lower()


# ── Attempt limit ────────────────────────────────────────────────


async def test_confirm_guest_registration_attempt_limit(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_lim@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await db_session.commit()

    guest_email = f"limit_{uuid4().hex[:6]}@test.com"

    await redis_mock.set(
        f"event_reg_verify:{guest_email}",
        json.dumps({
            "code": "123456",
            "event_id": str(event.id),
            "tariff_id": str(tariff.id),
        }),
    )

    await redis_mock.set(f"event_reg_attempts:{guest_email}", "5")

    resp = await client.post(
        f"/api/v1/events/{event.id}/confirm-guest-registration",
        json={
            "email": guest_email,
            "code": "123456",
            "tariff_id": str(tariff.id),
            "idempotency_key": uuid4().hex,
        },
    )

    assert resp.status_code == 422
    assert "Too many verification attempts" in resp.json()["error"]["message"]


# ── Send code rate limit ─────────────────────────────────────────


async def test_register_guest_send_code_rate_limit(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_rl@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=2000, member_price=1000)
    await db_session.commit()

    guest_email = f"ratelimit_{uuid4().hex[:6]}@test.com"

    await redis_mock.set(f"event_reg_send_count:{guest_email}", "3")

    resp = await client.post(
        f"/api/v1/events/{event.id}/register",
        json={
            "tariff_id": str(tariff.id),
            "idempotency_key": uuid4().hex,
            "guest_email": guest_email,
        },
    )

    assert resp.status_code == 422
    assert "Too many verification codes sent" in resp.json()["error"]["message"]


# ── Edge cases ───────────────────────────────────────────────────


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


async def test_register_guest_no_email(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_noeml@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/events/{event.id}/register",
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


async def test_register_after_cancelled_reuses_registration(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    """After payment/registration cancelled, user can register again and gets new payment_url."""
    from app.core.enums import EventRegistrationStatus
    from app.models.events import EventRegistration
    from app.models.subscriptions import Payment
    from tests.factories import create_event, create_event_tariff, create_user

    admin = await create_user(db_session, email="evt_admin_reuse@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event, price=3000, member_price=1500)
    await db_session.commit()

    mock_result = CreatePaymentResult(
        external_id="op_reuse1_" + uuid4().hex[:8],
        payment_url="https://moneta.test/pay/reuse1",
    )

    with patch("app.services.event_registration_service.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_gp.return_value = mock_provider

        resp = await client.post(
            f"/api/v1/events/{event.id}/register",
            headers=auth_headers_doctor,
            json={"tariff_id": str(tariff.id), "idempotency_key": "idem-reuse"},
        )

    assert resp.status_code == 201
    reg_id = resp.json()["registration_id"]

    reg = await db_session.get(EventRegistration, reg_id)
    reg.status = EventRegistrationStatus.CANCELLED  # type: ignore[assignment]
    result = await db_session.execute(
        select(Payment).where(Payment.event_registration_id == reg.id)
    )
    for p in result.scalars().all():
        p.status = "failed"  # type: ignore[assignment]
    tariff = await db_session.get(EventTariff, tariff.id)
    if tariff.seats_taken > 0:
        tariff.seats_taken -= 1  # type: ignore[assignment]
    await db_session.commit()

    mock_result2 = CreatePaymentResult(
        external_id="op_reuse2_" + uuid4().hex[:8],
        payment_url="https://moneta.test/pay/reuse2",
    )

    with patch("app.services.event_registration_service.get_provider") as mock_gp:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result2)
        mock_gp.return_value = mock_provider

        resp2 = await client.post(
            f"/api/v1/events/{event.id}/register",
            headers=auth_headers_doctor,
            json={"tariff_id": str(tariff.id), "idempotency_key": "idem-reuse2"},
        )

    assert resp2.status_code == 201
    data = resp2.json()
    assert data["registration_id"] == reg_id
    assert data["payment_url"] == "https://moneta.test/pay/reuse2"
    assert data["applied_price"] == 3000.0
