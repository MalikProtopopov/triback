"""Health and docs endpoint tests."""

from httpx import AsyncClient


async def test_health_ok(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "db" in data
    assert "redis" in data


async def test_docs_available(client: AsyncClient):
    resp = await client.get("/docs")
    assert resp.status_code == 200
