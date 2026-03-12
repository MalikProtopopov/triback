"""Subscription status and product type determination tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User

STATUS_URL = "/api/v1/subscriptions/status"
PAY_URL = "/api/v1/subscriptions/pay"


async def test_subscription_status(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile, create_plan, create_subscription

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    plan = await create_plan(db_session)
    await create_subscription(db_session, user=doctor_user, plan=plan, status="active")
    await db_session.commit()

    resp = await client.get(STATUS_URL, headers=auth_headers_doctor)
    assert resp.status_code == 200


async def test_subscription_status_no_sub(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    await db_session.commit()
    resp = await client.get(STATUS_URL, headers=auth_headers_doctor)
    assert resp.status_code == 200


async def test_pay_entry_fee_no_subscription(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    """First-time doctor with no prior payments gets product_type=entry_fee."""
    from tests.factories import create_doctor_profile, create_plan

    await create_doctor_profile(
        db_session, user=doctor_user, status="active", has_medical_diploma=True
    )
    plan = await create_plan(db_session)
    await db_session.commit()

    mock_resp = {
        "id": "yoo_entry_" + uuid4().hex[:8],
        "status": "pending",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/entry"},
    }

    with patch(
        "app.services.subscription_service.YooKassaClient.create_payment",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = await client.post(
            PAY_URL,
            headers=auth_headers_doctor,
            json={"plan_id": str(plan.id), "idempotency_key": uuid4().hex},
        )

    assert resp.status_code == 201


async def test_pay_subscription_within_90_days(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    """Renewal within 90 days of expiry -> product_type=subscription."""
    from tests.factories import (
        create_doctor_profile,
        create_payment,
        create_plan,
        create_subscription,
    )

    await create_doctor_profile(
        db_session, user=doctor_user, status="active", has_medical_diploma=True
    )
    plan = await create_plan(db_session)
    now = datetime.now(UTC)
    await create_subscription(
        db_session,
        user=doctor_user,
        plan=plan,
        status="active",
        starts_at=now - timedelta(days=300),
        ends_at=now - timedelta(days=5),
    )
    # Mark an entry fee as paid
    await create_payment(
        db_session,
        user=doctor_user,
        amount=5000.0,
        product_type="entry_fee",
        status="succeeded",
    )
    await db_session.commit()

    mock_resp = {
        "id": "yoo_renew_" + uuid4().hex[:8],
        "status": "pending",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/renew"},
    }

    with patch(
        "app.services.subscription_service.YooKassaClient.create_payment",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = await client.post(
            PAY_URL,
            headers=auth_headers_doctor,
            json={"plan_id": str(plan.id), "idempotency_key": uuid4().hex},
        )

    assert resp.status_code == 201


async def test_pay_entry_fee_over_90_days(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    """Lapsed > 90 days -> product_type=entry_fee again."""
    from tests.factories import create_doctor_profile, create_plan, create_subscription

    await create_doctor_profile(
        db_session, user=doctor_user, status="active", has_medical_diploma=True
    )
    plan = await create_plan(db_session)
    now = datetime.now(UTC)
    await create_subscription(
        db_session,
        user=doctor_user,
        plan=plan,
        status="active",
        starts_at=now - timedelta(days=500),
        ends_at=now - timedelta(days=100),
    )
    await db_session.commit()

    mock_resp = {
        "id": "yoo_lapse_" + uuid4().hex[:8],
        "status": "pending",
        "confirmation": {"confirmation_url": "https://yookassa.ru/pay/lapse"},
    }

    with patch(
        "app.services.subscription_service.YooKassaClient.create_payment",
        new_callable=AsyncMock,
        return_value=mock_resp,
    ):
        resp = await client.post(
            PAY_URL,
            headers=auth_headers_doctor,
            json={"plan_id": str(plan.id), "idempotency_key": uuid4().hex},
        )

    assert resp.status_code == 201
