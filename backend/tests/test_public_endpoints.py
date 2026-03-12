"""Tests for public endpoints — org docs, sitemap, robots, health."""

from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_article,
    create_doctor_profile,
    create_event,
    create_org_document,
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
