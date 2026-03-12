"""Admin doctor management tests."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

ADMIN_DOCTORS_URL = "/api/v1/admin/doctors"


async def test_admin_list_requires_auth(client: AsyncClient):
    resp = await client.get(ADMIN_DOCTORS_URL)
    assert resp.status_code == 401


async def test_admin_list_accountant_forbidden(
    client: AsyncClient, auth_headers_accountant: dict[str, str]
):
    resp = await client.get(ADMIN_DOCTORS_URL, headers=auth_headers_accountant)
    assert resp.status_code == 403


async def test_admin_list_success(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, status="pending_review")
    await db_session.commit()

    resp = await client.get(ADMIN_DOCTORS_URL, headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data


async def test_moderate_approve(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    profile = await create_doctor_profile(
        db_session, status="pending_review"
    )
    await db_session.commit()

    resp = await client.post(
        f"{ADMIN_DOCTORS_URL}/{profile.id}/moderate",
        headers=auth_headers_admin,
        json={"action": "approve"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["moderation_status"] == "approved"


async def test_moderate_reject_no_comment(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    profile = await create_doctor_profile(
        db_session, status="pending_review"
    )
    await db_session.commit()

    resp = await client.post(
        f"{ADMIN_DOCTORS_URL}/{profile.id}/moderate",
        headers=auth_headers_admin,
        json={"action": "reject"},
    )
    assert resp.status_code == 422


async def test_approve_draft(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile, create_profile_change

    profile = await create_doctor_profile(db_session, status="active")
    await create_profile_change(
        db_session, profile=profile, changes={"bio": "New bio text"}
    )
    await db_session.commit()

    resp = await client.post(
        f"{ADMIN_DOCTORS_URL}/{profile.id}/approve-draft",
        headers=auth_headers_admin,
        json={"action": "approve"},
    )
    assert resp.status_code == 200


async def test_toggle_active(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    profile = await create_doctor_profile(db_session, status="approved")
    await db_session.commit()

    resp = await client.post(
        f"{ADMIN_DOCTORS_URL}/{profile.id}/toggle-active",
        headers=auth_headers_admin,
        json={"is_public": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_public"] is True
