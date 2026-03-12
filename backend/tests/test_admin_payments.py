"""Tests for admin payment endpoints — list and manual payment."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import _make_auth_headers
from tests.factories import (
    create_doctor_profile,
    create_payment,
    create_plan,
    create_subscription,
    create_user,
)


async def test_admin_list_payments_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/admin/payments")
    assert resp.status_code == 401


async def test_admin_list_payments_requires_admin_role(
    client: AsyncClient, doctor_user
):
    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get("/api/v1/admin/payments", headers=headers)
    assert resp.status_code == 403


async def test_admin_list_payments(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user,
    auth_headers_admin,
):
    user = await create_user(db_session)
    await create_doctor_profile(db_session, user=user)
    await create_payment(db_session, user=user, status="succeeded", amount=5000.0)
    await create_payment(db_session, user=user, status="pending", amount=3000.0)

    resp = await client.get("/api/v1/admin/payments", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert "summary" in data
    assert data["summary"]["count_completed"] >= 1


async def test_admin_list_payments_filter_by_status(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user,
    auth_headers_admin,
):
    user = await create_user(db_session)
    await create_payment(db_session, user=user, status="succeeded")
    await create_payment(db_session, user=user, status="pending")

    resp = await client.get(
        "/api/v1/admin/payments?status=succeeded",
        headers=auth_headers_admin,
    )
    assert resp.status_code == 200
    data = resp.json()
    for item in data["data"]:
        assert item["status"] == "succeeded"


async def test_admin_manual_payment(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user,
    auth_headers_admin,
):
    user = await create_user(db_session)
    plan = await create_plan(db_session)
    sub = await create_subscription(
        db_session, user=user, plan=plan, status="pending_payment"
    )

    resp = await client.post(
        "/api/v1/admin/payments/manual",
        json={
            "user_id": str(user.id),
            "amount": 5000,
            "product_type": "subscription",
            "subscription_id": str(sub.id),
            "description": "Manual payment test",
        },
        headers=auth_headers_admin,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["payment_provider"] == "manual"
