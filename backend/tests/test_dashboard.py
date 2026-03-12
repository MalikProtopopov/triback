"""Tests for admin dashboard endpoint."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import _make_auth_headers
from tests.factories import (
    create_doctor_profile,
    create_event,
    create_payment,
    create_plan,
    create_subscription,
    create_user,
)


async def test_dashboard_requires_admin(client: AsyncClient, doctor_user):
    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get("/api/v1/admin/dashboard", headers=headers)
    assert resp.status_code == 403


async def test_dashboard_returns_metrics(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user,
    auth_headers_admin,
):
    user = await create_user(db_session)
    plan = await create_plan(db_session)
    await create_doctor_profile(db_session, user=user, status="active")
    await create_subscription(db_session, user=user, plan=plan, status="active")
    await create_payment(db_session, user=user, status="succeeded", amount=5000.0)
    await create_event(db_session, created_by=admin_user)

    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    assert "active_doctors" in data
    assert "active_subscriptions" in data
