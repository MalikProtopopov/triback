"""Tests for onboarding endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import _make_auth_headers
from tests.factories import (
    assign_role,
    create_doctor_profile,
    create_role,
    create_user,
)


@pytest.fixture
async def user_no_role(db_session: AsyncSession):
    return await create_user(db_session, email_verified_at=None)


@pytest.fixture
async def user_verified(db_session: AsyncSession):
    from datetime import UTC, datetime

    return await create_user(db_session, email_verified_at=datetime.now(UTC))


@pytest.fixture
def auth_for_user(user_verified):
    return _make_auth_headers(user_verified.id, "user")


@pytest.fixture
def auth_for_norole(user_no_role):
    return _make_auth_headers(user_no_role.id, "user")


async def test_onboarding_status_unverified(
    client: AsyncClient, user_no_role, auth_for_norole
):
    resp = await client.get("/api/v1/onboarding/status", headers=auth_for_norole)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email_verified"] is False
    assert data["next_step"] == "verify_email"


async def test_onboarding_status_verified_no_role(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    headers = _make_auth_headers(user_verified.id, "user")
    resp = await client.get("/api/v1/onboarding/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email_verified"] is True
    assert data["role_chosen"] is False
    assert data["next_step"] == "choose_role"


async def test_choose_role_doctor(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    await create_role(db_session, name="doctor")
    headers = _make_auth_headers(user_verified.id, "user")
    resp = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "doctor"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_step"] == "fill_profile"
    assert data["profile_id"] is not None


async def test_choose_role_user(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    await create_role(db_session, name="user")
    headers = _make_auth_headers(user_verified.id, "user")
    resp = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "user"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_step"] == "completed"


async def test_choose_role_already_chosen_conflict(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    role = await create_role(db_session, name="doctor")
    await assign_role(db_session, user_verified, role)

    headers = _make_auth_headers(user_verified.id, "doctor")
    resp = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "user"},
        headers=headers,
    )
    assert resp.status_code == 409


async def test_onboarding_submit_requires_diploma(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    role = await create_role(db_session, name="doctor")
    await assign_role(db_session, user_verified, role)
    await create_doctor_profile(
        db_session, user=user_verified, status="pending_review", has_medical_diploma=False
    )

    headers = _make_auth_headers(user_verified.id, "doctor")
    resp = await client.post("/api/v1/onboarding/submit", headers=headers)
    assert resp.status_code == 422


async def test_onboarding_submit_success(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    role = await create_role(db_session, name="doctor")
    await assign_role(db_session, user_verified, role)
    await create_doctor_profile(
        db_session, user=user_verified, status="pending_review", has_medical_diploma=True
    )

    headers = _make_auth_headers(user_verified.id, "doctor")
    resp = await client.post("/api/v1/onboarding/submit", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_step"] == "await_moderation"
