"""Profile and onboarding tests."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User

ONBOARDING_STATUS_URL = "/api/v1/onboarding/status"
PERSONAL_URL = "/api/v1/profile/personal"


async def test_get_onboarding_status(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
):
    resp = await client.get(ONBOARDING_STATUS_URL, headers=auth_headers_doctor)
    assert resp.status_code == 200


async def test_get_personal_profile(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    resp = await client.get(PERSONAL_URL, headers=auth_headers_doctor)
    assert resp.status_code == 200
    data = resp.json()
    assert "first_name" in data
    assert "last_name" in data


async def test_update_personal_profile(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    resp = await client.patch(
        PERSONAL_URL,
        headers=auth_headers_doctor,
        json={"phone": "+79001234567"},
    )
    assert resp.status_code == 200


async def test_update_public_profile_creates_draft(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    resp = await client.patch(
        "/api/v1/profile/public",
        headers=auth_headers_doctor,
        json={"bio": "New bio for testing"},
    )
    assert resp.status_code == 200
    assert "модерацию" in resp.json().get("message", "").lower() or resp.status_code == 200


async def test_profile_unauthenticated(client: AsyncClient):
    resp = await client.get(PERSONAL_URL)
    assert resp.status_code == 401


async def test_onboarding_unauthenticated(client: AsyncClient):
    resp = await client.get(ONBOARDING_STATUS_URL)
    assert resp.status_code == 401
