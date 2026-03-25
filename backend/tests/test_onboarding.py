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
    return _make_auth_headers(user_verified.id, "pending")


@pytest.fixture
def auth_for_norole(user_no_role):
    return _make_auth_headers(user_no_role.id, "pending")


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
    headers = _make_auth_headers(user_verified.id, "pending")
    resp = await client.get("/api/v1/onboarding/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email_verified"] is True
    assert data["role_chosen"] is False
    assert data["next_step"] == "choose_role"
    assert data["onboarding_applicable"] is True
    assert data["can_upgrade_to_doctor"] is False
    assert "status_label" in data


async def test_choose_role_doctor(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    await create_role(db_session, name="doctor")
    headers = _make_auth_headers(user_verified.id, "pending")
    resp = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "doctor"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_step"] == "fill_profile"
    assert data["profile_id"] is not None
    assert data.get("access_token")


async def test_choose_role_user(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    await create_role(db_session, name="user")
    headers = _make_auth_headers(user_verified.id, "pending")
    resp = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "user"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_step"] == "completed"
    assert data.get("access_token")


async def test_upgrade_user_to_doctor(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    await create_role(db_session, name="user")
    await create_role(db_session, name="doctor")
    headers = _make_auth_headers(user_verified.id, "pending")
    r1 = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "user"},
        headers=headers,
    )
    assert r1.status_code == 200
    st = await client.get("/api/v1/onboarding/status", headers=headers)
    assert st.json()["can_upgrade_to_doctor"] is True

    r2 = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "doctor"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["next_step"] == "fill_profile"
    assert r2.json().get("access_token")


async def test_choose_role_idempotent_same_role(
    client: AsyncClient, db_session: AsyncSession, user_verified
):
    await create_role(db_session, name="doctor")
    headers = _make_auth_headers(user_verified.id, "pending")
    r1 = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "doctor"},
        headers=headers,
    )
    assert r1.status_code == 200
    r2 = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "doctor"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["message"] == "Роль уже выбрана"
    assert r2.json().get("access_token") is None


async def test_staff_onboarding_not_applicable(
    client: AsyncClient, auth_headers_admin: dict[str, str]
):
    resp = await client.get("/api/v1/onboarding/status", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_step"] == "not_applicable"
    assert data["onboarding_applicable"] is False


async def test_staff_choose_role_forbidden(
    client: AsyncClient, db_session: AsyncSession, auth_headers_admin: dict[str, str]
):
    await create_role(db_session, name="doctor")
    resp = await client.post(
        "/api/v1/onboarding/choose-role",
        json={"role": "doctor"},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 403


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
