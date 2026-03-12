"""Tests for SEO admin CRUD and public SEO endpoint."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


async def test_create_seo_page(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    admin_user: User,
    db_session: AsyncSession,
):
    resp = await client.post(
        "/api/v1/admin/seo-pages",
        headers=auth_headers_admin,
        json={"slug": "test-page", "title": "Test SEO", "description": "Test desc"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "test-page"
    assert data["title"] == "Test SEO"


async def test_list_seo_pages(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    admin_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_page_seo

    await create_page_seo(db_session, slug="seo-a", title="A")
    await create_page_seo(db_session, slug="seo-b", title="B")
    await db_session.commit()

    resp = await client.get("/api/v1/admin/seo-pages", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2


async def test_update_seo_page(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    admin_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_page_seo

    await create_page_seo(db_session, slug="update-me", title="Old")
    await db_session.commit()

    resp = await client.patch(
        "/api/v1/admin/seo-pages/update-me",
        headers=auth_headers_admin,
        json={"title": "New Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


async def test_delete_seo_page(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    admin_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_page_seo

    await create_page_seo(db_session, slug="delete-me", title="Delete")
    await db_session.commit()

    resp = await client.delete(
        "/api/v1/admin/seo-pages/delete-me", headers=auth_headers_admin
    )
    assert resp.status_code == 204

    resp = await client.get(
        "/api/v1/admin/seo-pages/delete-me", headers=auth_headers_admin
    )
    assert resp.status_code == 404


async def test_public_seo_endpoint(
    client: AsyncClient, db_session: AsyncSession
):
    from tests.factories import create_page_seo

    await create_page_seo(db_session, slug="homepage", title="Home")
    await db_session.commit()

    resp = await client.get("/api/v1/seo/homepage")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "homepage"


async def test_public_seo_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/seo/nonexistent-page")
    assert resp.status_code == 404
