"""Admin cities API — RBAC."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_city

ADMIN_CITIES_URL = "/api/v1/admin/cities"


async def test_list_cities_accountant_ok(
    client: AsyncClient,
    auth_headers_accountant: dict[str, str],
    db_session: AsyncSession,
):
    await create_city(db_session, name="Казань", slug="kazan")
    await db_session.commit()

    resp = await client.get(ADMIN_CITIES_URL, headers=auth_headers_accountant)
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert any(c.get("slug") == "kazan" for c in body["data"])


async def test_create_city_accountant_forbidden(
    client: AsyncClient,
    auth_headers_accountant: dict[str, str],
):
    resp = await client.post(
        ADMIN_CITIES_URL,
        headers=auth_headers_accountant,
        json={"name": "Новый город"},
    )
    assert resp.status_code == 403
