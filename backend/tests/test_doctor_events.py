"""Tests for doctor-facing events: my events list, galleries, recordings."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


async def test_my_events_empty(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
):
    resp = await client.get("/api/v1/profile/events", headers=auth_headers_doctor)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["data"] == []


async def test_my_events_with_registration(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_event,
        create_event_registration,
        create_event_tariff,
        create_user,
    )

    admin = await create_user(db_session, email="my_evt_admin@test.com")
    event = await create_event(db_session, created_by=admin, title="My Conference")
    tariff = await create_event_tariff(db_session, event=event)
    await create_event_registration(
        db_session, user=doctor_user, event=event, tariff=tariff, status="confirmed"
    )
    await db_session.commit()

    resp = await client.get("/api/v1/profile/events", headers=auth_headers_doctor)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["data"][0]["title"] == "My Conference"


async def test_my_events_pending_excluded(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_event,
        create_event_registration,
        create_event_tariff,
        create_user,
    )

    admin = await create_user(db_session, email="my_evt_admin2@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event)
    await create_event_registration(
        db_session, user=doctor_user, event=event, tariff=tariff, status="pending"
    )
    await db_session.commit()

    resp = await client.get("/api/v1/profile/events", headers=auth_headers_doctor)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_event_galleries_public(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from tests.factories import create_event, create_event_gallery, create_user

    admin = await create_user(db_session, email="gal_admin@test.com")
    event = await create_event(db_session, created_by=admin)
    await create_event_gallery(db_session, event=event, title="Public Gallery", access_level="public")
    await create_event_gallery(db_session, event=event, title="Private Gallery", access_level="members_only")
    await db_session.commit()

    resp = await client.get(f"/api/v1/events/{event.id}/galleries")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Public Gallery"


async def test_event_galleries_member_access(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_event,
        create_event_gallery,
        create_plan,
        create_subscription,
        create_user,
    )

    admin = await create_user(db_session, email="gal_admin2@test.com")
    event = await create_event(db_session, created_by=admin)
    await create_event_gallery(db_session, event=event, title="Public Gallery", access_level="public")
    await create_event_gallery(db_session, event=event, title="Members Gallery", access_level="members_only")
    plan = await create_plan(db_session)
    await create_subscription(db_session, user=doctor_user, plan=plan, status="active")
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/events/{event.id}/galleries",
        headers=auth_headers_doctor,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2


async def test_organization_documents(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from tests.factories import create_org_document

    await create_org_document(db_session, title="Charter", slug="charter")
    await db_session.commit()

    resp = await client.get("/api/v1/organization-documents")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1
    assert data[0]["title"] == "Charter"


async def test_sitemap_xml(client: AsyncClient):
    resp = await client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "urlset" in resp.text


async def test_robots_txt(client: AsyncClient):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert "User-agent" in resp.text
    assert "Sitemap" in resp.text
