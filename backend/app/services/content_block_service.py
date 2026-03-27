"""Service for content blocks CRUD and reordering."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppValidationError, NotFoundError
from app.models.content import ContentBlock
from app.schemas.content_blocks import ContentBlockListResponse, ContentBlockResponse
from app.services import file_service

logger = structlog.get_logger(__name__)


def _validate_gallery_metadata(meta: dict[str, Any] | None) -> None:
    """Require non-empty ``images`` with ``url`` for gallery blocks."""
    if not meta:
        raise AppValidationError("Блок gallery: укажите block_metadata")
    images = meta.get("images")
    if not isinstance(images, list) or len(images) == 0:
        raise AppValidationError(
            "Блок gallery: в block_metadata нужен непустой массив images"
        )
    for i, item in enumerate(images):
        if not isinstance(item, dict):
            raise AppValidationError(
                f"Блок gallery: images[{i}] должен быть объектом с полем url"
            )
        raw = item.get("url")
        if not isinstance(raw, str) or not raw.strip():
            raise AppValidationError(
                f"Блок gallery: images[{i}].url обязательно (S3-ключ или URL)"
            )


async def list_blocks_for_entity(
    db: AsyncSession, entity_type: str, entity_id: UUID
) -> list[ContentBlock]:
    """Return content blocks for an entity, sorted by sort_order (ASC)."""
    result = await db.execute(
        select(ContentBlock)
        .where(
            ContentBlock.entity_type == entity_type,
            ContentBlock.entity_id == entity_id,
        )
        .order_by(ContentBlock.sort_order.asc())
    )
    return list(result.scalars().all())


def _block_to_response(block: ContentBlock) -> ContentBlockResponse:
    return ContentBlockResponse(
        id=block.id,
        entity_type=block.entity_type,
        entity_id=block.entity_id,
        locale=block.locale,
        block_type=block.block_type,
        sort_order=block.sort_order,
        title=block.title,
        content=block.content,
        media_url=file_service.build_media_url(block.media_url),
        thumbnail_url=file_service.build_media_url(block.thumbnail_url),
        link_url=block.link_url,
        link_label=block.link_label,
        device_type=block.device_type,
        block_metadata=file_service.enrich_block_metadata_urls(
            block.block_metadata, block.block_type
        ),
        created_at=block.created_at,
        updated_at=block.updated_at,
    )


class ContentBlockService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_blocks(
        self,
        entity_type: str,
        entity_id: UUID,
        locale: str = "ru",
    ) -> ContentBlockListResponse:
        q = (
            select(ContentBlock)
            .where(
                ContentBlock.entity_type == entity_type,
                ContentBlock.entity_id == entity_id,
                ContentBlock.locale == locale,
            )
            .order_by(ContentBlock.sort_order.asc())
        )
        count_q = select(func.count(ContentBlock.id)).where(
            ContentBlock.entity_type == entity_type,
            ContentBlock.entity_id == entity_id,
            ContentBlock.locale == locale,
        )
        total = (await self.db.execute(count_q)).scalar() or 0
        blocks = (await self.db.execute(q)).scalars().all()
        return ContentBlockListResponse(
            data=[_block_to_response(b) for b in blocks],
            total=total,
        )

    async def create_block(self, data: dict[str, Any]) -> ContentBlockResponse:
        if data.get("block_type") == "gallery":
            _validate_gallery_metadata(data.get("block_metadata"))
        block = ContentBlock(**data)
        self.db.add(block)
        await self.db.commit()
        await self.db.refresh(block)
        logger.info(
            "content_block_created",
            block_id=str(block.id),
            entity_type=data["entity_type"],
        )
        return _block_to_response(block)

    async def update_block(
        self, block_id: UUID, data: dict[str, Any]
    ) -> ContentBlockResponse:
        block = await self.db.get(ContentBlock, block_id)
        if not block:
            raise NotFoundError("Content block not found")

        merged_type = data.get("block_type", block.block_type)
        merged_meta = data.get("block_metadata", block.block_metadata)
        if merged_type == "gallery":
            _validate_gallery_metadata(merged_meta)

        for key, value in data.items():
            setattr(block, key, value)

        await self.db.commit()
        await self.db.refresh(block)
        return _block_to_response(block)

    async def delete_block(self, block_id: UUID) -> None:
        block = await self.db.get(ContentBlock, block_id)
        if not block:
            raise NotFoundError("Content block not found")
        await self.db.delete(block)
        await self.db.commit()

    async def reorder_blocks(
        self, items: list[dict[str, Any]]
    ) -> list[ContentBlockResponse]:
        result = []
        for item in items:
            block = await self.db.get(ContentBlock, item["id"])
            if not block:
                raise NotFoundError(f"Content block {item['id']} not found")
            block.sort_order = item["sort_order"]
            result.append(block)
        await self.db.commit()
        for b in result:
            await self.db.refresh(b)
        return [_block_to_response(b) for b in sorted(result, key=lambda b: b.sort_order)]
