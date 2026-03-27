"""Tests for content block metadata URL enrichment and public gallery responses."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import ContentBlock
from app.services import file_service
from tests.factories import create_article, create_user


async def test_create_gallery_block_requires_images(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict[str, str],
) -> None:
    admin = await create_user(db_session)
    article = await create_article(
        db_session, author=admin, slug="gval", status="published"
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/admin/content-blocks",
        headers=auth_headers_admin,
        json={
            "entity_type": "article",
            "entity_id": str(article.id),
            "block_type": "gallery",
            "block_metadata": {"images": []},
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "images" in body["error"]["message"].lower()


def test_enrich_block_metadata_urls_gallery_resolves_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.config.settings.S3_PUBLIC_URL", "https://cdn.example.com"
    )
    meta = {"images": [{"url": "media-lib/a.jpg", "alt": "A"}]}
    out = file_service.enrich_block_metadata_urls(meta, "gallery")
    assert out is not None
    assert out["images"][0]["url"] == "https://cdn.example.com/media-lib/a.jpg"
    # original dict unchanged (deepcopy)
    assert meta["images"][0]["url"] == "media-lib/a.jpg"


def test_enrich_block_metadata_urls_leaves_absolute_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.config.settings.S3_PUBLIC_URL", "https://cdn.example.com"
    )
    meta = {"images": [{"url": "https://other.com/p.png", "alt": "x"}]}
    out = file_service.enrich_block_metadata_urls(meta, "gallery")
    assert out["images"][0]["url"] == "https://other.com/p.png"


def test_enrich_block_metadata_urls_non_gallery_returns_same_reference() -> None:
    meta = {"foo": "bar"}
    out = file_service.enrich_block_metadata_urls(meta, "text")
    assert out is meta


async def test_public_article_gallery_block_metadata_resolved(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.core.config.settings.S3_PUBLIC_URL", "https://assets.test"
    )
    admin = await create_user(db_session)
    article = await create_article(
        db_session, author=admin, slug="with-gallery", status="published"
    )
    block = ContentBlock(
        entity_type="article",
        entity_id=article.id,
        locale="ru",
        block_type="gallery",
        sort_order=0,
        title="Gallery",
        block_metadata={
            "images": [{"url": "uploads/g1.jpg", "alt": "One"}],
        },
        device_type="both",
    )
    db_session.add(block)
    await db_session.commit()

    resp = await client.get("/api/v1/articles/with-gallery")
    assert resp.status_code == 200
    data = resp.json()
    blocks = data["content_blocks"]
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == "gallery"
    assert blocks[0]["block_metadata"]["images"][0]["url"] == (
        "https://assets.test/uploads/g1.jpg"
    )
