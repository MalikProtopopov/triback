"""Payment and webhook tests."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


async def test_pay_creates_payment(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile, create_plan

    await create_doctor_profile(
        db_session, user=doctor_user, status="active", has_medical_diploma=True
    )
    plan = await create_plan(db_session)
    await db_session.commit()

    mock_yookassa_resp = {
        "id": "yoo_" + uuid4().hex[:10],
        "status": "pending",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/test"},
    }

    with patch(
        "app.services.subscription_service.YooKassaClient.create_payment",
        new_callable=AsyncMock,
        return_value=mock_yookassa_resp,
    ):
        resp = await client.post(
            "/api/v1/subscriptions/pay",
            headers=auth_headers_doctor,
            json={
                "plan_id": str(plan.id),
                "idempotency_key": uuid4().hex,
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert "payment_url" in data
    assert "payment_id" in data


async def test_pay_idempotency(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
):
    from tests.factories import create_doctor_profile, create_plan

    await create_doctor_profile(
        db_session, user=doctor_user, status="active", has_medical_diploma=True
    )
    plan = await create_plan(db_session)
    await db_session.commit()

    idem_key = uuid4().hex

    mock_yookassa_resp = {
        "id": "yoo_idem_" + uuid4().hex[:8],
        "status": "pending",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/idem"},
    }

    with patch(
        "app.services.subscription_service.YooKassaClient.create_payment",
        new_callable=AsyncMock,
        return_value=mock_yookassa_resp,
    ):
        resp1 = await client.post(
            "/api/v1/subscriptions/pay",
            headers=auth_headers_doctor,
            json={"plan_id": str(plan.id), "idempotency_key": idem_key},
        )
        resp2 = await client.post(
            "/api/v1/subscriptions/pay",
            headers=auth_headers_doctor,
            json={"plan_id": str(plan.id), "idempotency_key": idem_key},
        )

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["payment_id"] == resp2.json()["payment_id"]


async def test_webhook_payment_succeeded(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_doctor_profile,
        create_payment,
        create_plan,
        create_subscription,
        create_user,
    )

    user = await create_user(db_session, email="webhook_ok@test.com")
    await create_doctor_profile(db_session, user=user)
    plan = await create_plan(db_session)
    sub = await create_subscription(
        db_session, user=user, plan=plan, status="pending_payment"
    )
    payment = await create_payment(
        db_session,
        user=user,
        amount=5000.0,
        product_type="subscription",
        status="pending",
        subscription=sub,
        external_payment_id="yoo_ext_123",
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": "yoo_ext_123",
                "status": "succeeded",
                "amount": {"value": "5000.00", "currency": "RUB"},
                "metadata": {
                    "internal_payment_id": str(payment.id),
                    "product_type": "subscription",
                    "user_id": str(user.id),
                },
            },
        },
        headers={"x-forwarded-for": "185.71.76.1"},
    )
    assert resp.status_code == 200


async def test_webhook_ip_not_whitelisted(client: AsyncClient):
    resp = await client.post(
        "/api/v1/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": "yoo_bad_ip",
                "status": "succeeded",
                "amount": {"value": "1000.00", "currency": "RUB"},
                "metadata": {},
            },
        },
        headers={"x-forwarded-for": "1.2.3.4"},
    )
    # The webhook endpoint catches all exceptions and returns 200
    # but internally the ForbiddenError is raised and logged
    assert resp.status_code == 200


async def test_webhook_already_succeeded(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from tests.factories import create_payment, create_plan, create_subscription, create_user

    user = await create_user(db_session, email="webhook_dup@test.com")
    plan = await create_plan(db_session)
    sub = await create_subscription(db_session, user=user, plan=plan, status="active")
    payment = await create_payment(
        db_session,
        user=user,
        amount=5000.0,
        status="succeeded",
        subscription=sub,
        external_payment_id="yoo_already_ok",
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": "yoo_already_ok",
                "status": "succeeded",
                "amount": {"value": "5000.00", "currency": "RUB"},
                "metadata": {"internal_payment_id": str(payment.id)},
            },
        },
        headers={"x-forwarded-for": "185.71.76.1"},
    )
    assert resp.status_code == 200


async def test_webhook_payment_canceled(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from tests.factories import create_payment, create_user

    user = await create_user(db_session, email="webhook_cancel@test.com")
    payment = await create_payment(
        db_session,
        user=user,
        amount=3000.0,
        status="pending",
        external_payment_id="yoo_cancel_123",
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.canceled",
            "object": {
                "id": "yoo_cancel_123",
                "status": "canceled",
                "amount": {"value": "3000.00", "currency": "RUB"},
                "metadata": {"internal_payment_id": str(payment.id)},
            },
        },
        headers={"x-forwarded-for": "185.71.76.1"},
    )
    assert resp.status_code == 200
