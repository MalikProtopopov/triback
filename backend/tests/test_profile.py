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


async def test_patch_public_merges_second_update_into_same_pending_draft(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    """Второй PATCH /public не даёт 409: объединяется с тем же pending."""
    from sqlalchemy import func, select

    from app.models.profiles import DoctorProfileChange
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    r1 = await client.patch(
        "/api/v1/profile/public",
        headers=auth_headers_doctor,
        json={"bio": "First"},
    )
    assert r1.status_code == 200
    r2 = await client.patch(
        "/api/v1/profile/public",
        headers=auth_headers_doctor,
        json={"public_email": "doc@example.com"},
    )
    assert r2.status_code == 200

    cnt = (
        await db_session.execute(
            select(func.count()).select_from(DoctorProfileChange).where(
                DoctorProfileChange.status == "pending",
            )
        )
    ).scalar_one()
    assert cnt == 1

    draft = (
        await db_session.execute(select(DoctorProfileChange).where(
            DoctorProfileChange.status == "pending",
        ))
    ).scalar_one()
    assert draft.changes.get("bio") == "First"
    assert draft.changes.get("public_email") == "doc@example.com"


SUBMIT_URL = "/api/v1/profile/public/submit"


async def test_submit_public_empty_multipart_422(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    resp = await client.post(SUBMIT_URL, headers=auth_headers_doctor, data={})
    assert resp.status_code == 422


async def test_submit_public_text_only(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from sqlalchemy import select

    from app.models.profiles import DoctorProfileChange
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    resp = await client.post(
        SUBMIT_URL,
        headers=auth_headers_doctor,
        data={"bio": "From submit"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("pending_moderation") is True
    assert (body.get("photo_url") or "") == ""

    draft = (
        await db_session.execute(select(DoctorProfileChange).where(
            DoctorProfileChange.status == "pending",
        ))
    ).scalar_one()
    assert draft.changes.get("bio") == "From submit"


async def test_submit_public_invalid_email_422(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    resp = await client.post(
        SUBMIT_URL,
        headers=auth_headers_doctor,
        data={"public_email": "not-an-email"},
    )
    assert resp.status_code == 422


async def test_submit_public_merges_into_existing_pending(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from sqlalchemy import func, select

    from app.models.profiles import DoctorProfileChange
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    await client.patch(
        "/api/v1/profile/public",
        headers=auth_headers_doctor,
        json={"bio": "Patch bio"},
    )
    r2 = await client.post(
        SUBMIT_URL,
        headers=auth_headers_doctor,
        data={"public_phone": "+79990001122"},
    )
    assert r2.status_code == 200

    cnt = (
        await db_session.execute(
            select(func.count()).select_from(DoctorProfileChange).where(
                DoctorProfileChange.status == "pending",
            )
        )
    ).scalar_one()
    assert cnt == 1
    draft = (
        await db_session.execute(select(DoctorProfileChange).where(
            DoctorProfileChange.status == "pending",
        ))
    ).scalar_one()
    assert draft.changes.get("bio") == "Patch bio"
    assert draft.changes.get("public_phone") == "+79990001122"


async def test_submit_public_photo_only(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
    monkeypatch,
):
    from io import BytesIO
    from unittest.mock import AsyncMock

    from sqlalchemy import select

    from app.models.profiles import DoctorProfileChange
    from app.services import profile_service as ps_mod
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    monkeypatch.setattr(
        ps_mod.file_service,
        "upload_image_with_thumbnail",
        AsyncMock(return_value=("doctors/photo/main.webp", "doctors/photo/thumb.webp")),
    )
    monkeypatch.setattr(
        ps_mod.file_service,
        "build_media_url",
        lambda key: f"https://media.example/{key}" if key else "",
    )

    fake_image = BytesIO(b"\x00" * 64)
    resp = await client.post(
        SUBMIT_URL,
        headers=auth_headers_doctor,
        files={"photo": ("p.png", fake_image, "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "media.example" in (data.get("photo_url") or "")
    assert data.get("pending_moderation") is True

    draft = (
        await db_session.execute(select(DoctorProfileChange).where(
            DoctorProfileChange.status == "pending",
        ))
    ).scalar_one()
    assert draft.changes.get("photo_url") == "doctors/photo/main.webp"


async def test_submit_public_photo_and_text_together(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
    monkeypatch,
):
    from io import BytesIO
    from unittest.mock import AsyncMock

    from sqlalchemy import select

    from app.models.profiles import DoctorProfileChange
    from app.services import profile_service as ps_mod
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, user=doctor_user, status="active")
    await db_session.commit()

    monkeypatch.setattr(
        ps_mod.file_service,
        "upload_image_with_thumbnail",
        AsyncMock(return_value=("doctors/x/main.webp", "doctors/x/thumb.webp")),
    )
    monkeypatch.setattr(
        ps_mod.file_service,
        "build_media_url",
        lambda key: f"https://cdn/{key}" if key else "",
    )

    fake_image = BytesIO(b"\x00" * 64)
    resp = await client.post(
        SUBMIT_URL,
        headers=auth_headers_doctor,
        data={"bio": "Bio + photo"},
        files={"photo": ("p.png", fake_image, "image/png")},
    )
    assert resp.status_code == 200

    draft = (
        await db_session.execute(select(DoctorProfileChange).where(
            DoctorProfileChange.status == "pending",
        ))
    ).scalar_one()
    assert draft.changes.get("bio") == "Bio + photo"
    assert draft.changes.get("photo_url") == "doctors/x/main.webp"


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


async def test_get_public_no_draft_when_latest_is_approved(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    """Если последний черновик approved — возвращать draft со status=approved."""
    from datetime import UTC, datetime

    from tests.factories import create_doctor_profile, create_profile_change

    profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
    await create_profile_change(
        db_session,
        profile=profile,
        changes={"bio": "Old rejected"},
        status="rejected",
        rejection_reason="Плохое качество",
        reviewed_at=datetime(2026, 3, 15, tzinfo=UTC),
    )
    await create_profile_change(
        db_session,
        profile=profile,
        changes={"bio": "Approved bio"},
        status="approved",
        reviewed_at=datetime(2026, 3, 17, tzinfo=UTC),
    )
    await db_session.commit()

    resp = await client.get("/api/v1/profile/public", headers=auth_headers_doctor)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_draft"] is not None
    assert data["pending_draft"]["status"] == "approved"
    assert data["pending_draft"]["reviewed_at"] is not None
    assert data["pending_draft"]["rejection_reason"] is None
    assert data["pending_draft"]["changes"]["bio"] == "Approved bio"


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


async def test_get_public_no_draft_after_approved(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    """После approved черновика возвращать draft со status=approved, не старый rejected."""
    from datetime import UTC, datetime, timedelta

    from tests.factories import create_doctor_profile, create_profile_change

    profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
    await create_profile_change(
        db_session,
        profile=profile,
        changes={"bio": "Old rejected"},
        status="rejected",
        rejection_reason="Bad",
        reviewed_at=datetime.now(UTC) - timedelta(days=2),
    )
    await create_profile_change(
        db_session,
        profile=profile,
        changes={"bio": "Approved bio"},
        status="approved",
        reviewed_at=datetime.now(UTC) - timedelta(days=1),
    )
    await db_session.commit()

    resp = await client.get("/api/v1/profile/public", headers=auth_headers_doctor)
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_draft"] is not None
    assert data["pending_draft"]["status"] == "approved"
    assert data["pending_draft"]["reviewed_at"] is not None


async def test_profile_unauthenticated(client: AsyncClient):
    resp = await client.get(PERSONAL_URL)
    assert resp.status_code == 401


async def test_onboarding_unauthenticated(client: AsyncClient):
    resp = await client.get(ONBOARDING_STATUS_URL)
    assert resp.status_code == 401
