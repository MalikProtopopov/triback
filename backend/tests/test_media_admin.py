"""Tests for admin media library API."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_asset import MediaAsset


@pytest.fixture
def mock_upload_file(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake(file, path, allowed_types=None, max_size_mb=5):  # noqa: ANN001
        return "media-library/fake-uuid.jpg"

    monkeypatch.setattr(
        "app.services.media_admin_service.file_service.upload_file",
        _fake,
    )


async def test_admin_media_upload_registers_row(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict[str, str],
    mock_upload_file: None,
) -> None:
    files = {"file": ("shot.png", b"\x89PNG\r\n\x1a\n\x00", "image/png")}
    resp = await client.post(
        "/api/v1/admin/media",
        headers=auth_headers_admin,
        files=files,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["s3_key"] == "media-library/fake-uuid.jpg"
    assert data["id"]

    row = (
        await db_session.execute(select(MediaAsset).where(MediaAsset.id == data["id"]))
    ).scalar_one()
    assert row.s3_key == "media-library/fake-uuid.jpg"


async def test_admin_media_list(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict[str, str],
    mock_upload_file: None,
) -> None:
    files = {"file": ("a.png", b"\x89PNG\r\n\x1a\n\x00", "image/png")}
    await client.post(
        "/api/v1/admin/media",
        headers=auth_headers_admin,
        files=files,
    )
    resp = await client.get(
        "/api/v1/admin/media",
        headers=auth_headers_admin,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert len(body["data"]) >= 1
    assert body["data"][0]["s3_key"]


async def test_admin_media_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/admin/media")
    assert resp.status_code == 401
