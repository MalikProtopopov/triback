"""Tests for public endpoints — org docs, sitemap, robots, health."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_article,
    create_doctor_profile,
    create_event,
    create_org_document,
    create_plan,
    create_subscription,
    create_user,
)


async def test_health_check(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "db" in data
    assert "redis" in data


async def test_robots_txt(client: AsyncClient):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert "User-agent: *" in resp.text
    assert "Sitemap:" in resp.text


async def test_sitemap_xml(
    client: AsyncClient, db_session: AsyncSession, redis_mock: AsyncMock
):
    admin = await create_user(db_session)
    await create_doctor_profile(db_session, user=admin, status="active")
    await create_event(db_session, created_by=admin)
    await create_article(db_session, author=admin)

    resp = await client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "urlset" in resp.text
    assert "xml" in resp.headers["content-type"]


async def test_organization_documents(
    client: AsyncClient, db_session: AsyncSession
):
    await create_org_document(db_session, title="Privacy Policy")
    await create_org_document(db_session, title="Terms of Service")

    resp = await client.get("/api/v1/organization-documents")
    assert resp.status_code == 200
    data = resp.json()
    items = data.get("data", data) if isinstance(data, dict) else data
    assert len(items) >= 2


async def test_list_cities(client: AsyncClient, db_session: AsyncSession):
    from tests.factories import create_city

    await create_city(db_session, name="Moscow")
    resp = await client.get("/api/v1/cities")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


async def test_list_events_public(
    client: AsyncClient, db_session: AsyncSession
):
    admin = await create_user(db_session)
    await create_event(db_session, created_by=admin, status="upcoming")

    resp = await client.get("/api/v1/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "total" in data


async def test_public_settings_no_auth(client: AsyncClient, db_session: AsyncSession):
    """GET /settings/public returns public settings without auth."""
    resp = await client.get("/api/v1/settings/public")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert isinstance(data["data"], dict)


# ── Subscription filtering in public doctor catalog ──────────────


async def test_list_doctors_with_active_subscription(
    client: AsyncClient, db_session: AsyncSession, redis_mock: AsyncMock
):
    """Doctor with active subscription appears in public catalog."""
    user = await create_user(db_session)
    await create_doctor_profile(db_session, user=user, status="active")
    plan = await create_plan(db_session)
    await create_subscription(
        db_session,
        user=user,
        plan=plan,
        status="active",
        ends_at=datetime.now(UTC) + timedelta(days=180),
    )

    resp = await client.get("/api/v1/doctors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


async def test_list_doctors_without_subscription_hidden(
    client: AsyncClient, db_session: AsyncSession, redis_mock: AsyncMock
):
    """Doctor with status=active but NO subscription is hidden from catalog."""
    user = await create_user(db_session)
    await create_doctor_profile(db_session, user=user, status="active")

    resp = await client.get("/api/v1/doctors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


async def test_list_doctors_expired_subscription_hidden(
    client: AsyncClient, db_session: AsyncSession, redis_mock: AsyncMock
):
    """Doctor whose subscription has expired is hidden from catalog."""
    user = await create_user(db_session)
    await create_doctor_profile(db_session, user=user, status="active")
    plan = await create_plan(db_session)
    await create_subscription(
        db_session,
        user=user,
        plan=plan,
        status="active",
        starts_at=datetime.now(UTC) - timedelta(days=400),
        ends_at=datetime.now(UTC) - timedelta(days=1),
    )

    resp = await client.get("/api/v1/doctors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


async def test_get_doctor_without_subscription_404(
    client: AsyncClient, db_session: AsyncSession, redis_mock: AsyncMock
):
    """GET /doctors/{slug} returns 404 when doctor has no active subscription."""
    user = await create_user(db_session)
    profile = await create_doctor_profile(db_session, user=user, status="active")

    resp = await client.get(f"/api/v1/doctors/{profile.slug}")
    assert resp.status_code == 404


async def test_get_doctor_with_active_subscription(
    client: AsyncClient, db_session: AsyncSession, redis_mock: AsyncMock
):
    """GET /doctors/{slug} succeeds when doctor has active subscription."""
    user = await create_user(db_session)
    profile = await create_doctor_profile(db_session, user=user, status="active")
    plan = await create_plan(db_session)
    await create_subscription(
        db_session,
        user=user,
        plan=plan,
        status="active",
        ends_at=datetime.now(UTC) + timedelta(days=180),
    )

    resp = await client.get(f"/api/v1/doctors/{profile.slug}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == profile.slug


async def test_list_doctors_filter_by_specialization_substring(
    client: AsyncClient, db_session: AsyncSession, redis_mock: AsyncMock
):
    user = await create_user(db_session)
    await create_doctor_profile(
        db_session,
        user=user,
        status="active",
        specialization="Трихолог, косметолог",
    )
    plan = await create_plan(db_session)
    await create_subscription(
        db_session,
        user=user,
        plan=plan,
        status="active",
        ends_at=datetime.now(UTC) + timedelta(days=180),
    )
    await db_session.commit()

    resp = await client.get("/api/v1/doctors?specialization=космет")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any("космет" in (row.get("specialization") or "").lower() for row in data["data"])


async def test_get_doctor_detail_includes_specialization_text(
    client: AsyncClient, db_session: AsyncSession, redis_mock: AsyncMock
):
    user = await create_user(db_session)
    profile = await create_doctor_profile(
        db_session,
        user=user,
        status="active",
        specialization="Врач-трихолог",
    )
    plan = await create_plan(db_session)
    await create_subscription(
        db_session,
        user=user,
        plan=plan,
        status="active",
        ends_at=datetime.now(UTC) + timedelta(days=180),
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/doctors/{profile.slug}")
    assert resp.status_code == 200
    assert resp.json().get("specialization") == "Врач-трихолог"


# ── Photo moderation via draft ───────────────────────────────────


async def test_photo_upload_creates_pending_draft(
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
    auth_headers_doctor,
    monkeypatch,
):
    """POST /profile/photo creates a DoctorProfileChange draft instead of updating directly."""
    from unittest.mock import AsyncMock as AM

    from app.models.profiles import DoctorProfileChange
    from app.services import profile_service as ps_mod

    await create_doctor_profile(db_session, user=doctor_user, status="active")

    mock_upload = AM(return_value=("doctors/photo/main.webp", "doctors/photo/thumb.webp"))
    monkeypatch.setattr(ps_mod.file_service, "upload_image_with_thumbnail", mock_upload)

    from io import BytesIO

    fake_image = BytesIO(b"\x00" * 64)

    resp = await client.post(
        "/api/v1/profile/photo",
        files={"file": ("test.png", fake_image, "image/png")},
        headers=auth_headers_doctor,
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["pending_moderation"] is True

    from sqlalchemy import select

    result = await db_session.execute(
        select(DoctorProfileChange).where(
            DoctorProfileChange.status == "pending",
        )
    )
    draft = result.scalar_one_or_none()
    assert draft is not None
    assert "photo_url" in draft.changes
    assert "photo_url" in draft.changed_fields
