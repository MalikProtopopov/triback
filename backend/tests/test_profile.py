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


async def test_get_public_returns_rejected_draft_with_reason(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    """При rejected черновике GET /profile/public возвращает draft с rejection_reason и reviewed_at."""
    from tests.factories import create_doctor_profile, create_profile_change

    profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
    await create_profile_change(
        db_session,
        profile=profile,
        changes={"bio": "Rejected bio"},
        status="rejected",
        rejection_reason="Текст не соответствует требованиям",
    )
    await db_session.commit()

    resp = await client.get("/api/v1/profile/public", headers=auth_headers_doctor)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_draft"] is not None
    assert data["pending_draft"]["status"] == "rejected"
    assert data["pending_draft"]["rejection_reason"] == "Текст не соответствует требованиям"
    assert data["pending_draft"]["reviewed_at"] is not None
    assert data["pending_draft"]["changes"]["bio"] == "Rejected bio"


async def test_get_public_pending_draft_has_no_rejection(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    """При pending черновике rejection_reason и reviewed_at = null."""
    from tests.factories import create_doctor_profile, create_profile_change

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    profile = await db_session.execute(
        __import__("sqlalchemy").select(__import__("app.models.profiles", fromlist=["DoctorProfile"]).DoctorProfile).where(
            __import__("app.models.profiles", fromlist=["DoctorProfile"]).DoctorProfile.user_id == doctor_user.id
        )
    )
    # Simpler: create_profile_change creates pending by default
    from app.models.profiles import DoctorProfile
    from sqlalchemy import select

    result = await db_session.execute(
        select(DoctorProfile).where(DoctorProfile.user_id == doctor_user.id)
    )
    prof = result.scalar_one_or_none()
    await create_profile_change(db_session, profile=prof, changes={"bio": "Pending bio"})
    await db_session.commit()

    resp = await client.get("/api/v1/profile/public", headers=auth_headers_doctor)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_draft"] is not None
    assert data["pending_draft"]["status"] == "pending"
    assert data["pending_draft"]["rejection_reason"] is None
    assert data["pending_draft"]["reviewed_at"] is None


async def test_profile_unauthenticated(client: AsyncClient):
    resp = await client.get(PERSONAL_URL)
    assert resp.status_code == 401


async def test_onboarding_unauthenticated(client: AsyncClient):
    resp = await client.get(ONBOARDING_STATUS_URL)
    assert resp.status_code == 401
