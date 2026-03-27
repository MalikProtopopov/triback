"""Admin media library — upload to S3 and list registered keys."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_asset import MediaAsset
from app.schemas.media_admin import (
    MediaAssetItem,
    MediaAssetListResponse,
    MediaUploadResponse,
)
from app.services import file_service

logger = structlog.get_logger(__name__)


class MediaAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upload(self, file: UploadFile, uploaded_by: UUID) -> MediaUploadResponse:
        s3_key = await file_service.upload_file(
            file,
            path="media-library",
            allowed_types=file_service.IMAGE_MIMES,
            max_size_mb=10,
        )
        row = MediaAsset(
            s3_key=s3_key,
            original_filename=file.filename,
            mime_type=file.content_type,
            uploaded_by=uploaded_by,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        logger.info("media_asset_created", media_id=str(row.id), s3_key=s3_key)
        return MediaUploadResponse(
            id=row.id,
            s3_key=row.s3_key,
            public_url=file_service.build_media_url(row.s3_key),
            original_filename=row.original_filename,
            mime_type=row.mime_type,
        )

    async def list_assets(
        self, *, limit: int = 20, offset: int = 0
    ) -> MediaAssetListResponse:
        count_q = select(func.count(MediaAsset.id))
        total = (await self.db.execute(count_q)).scalar() or 0
        q = (
            select(MediaAsset)
            .order_by(MediaAsset.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.db.execute(q)).scalars().all()
        data = [
            MediaAssetItem(
                id=r.id,
                s3_key=r.s3_key,
                public_url=file_service.build_media_url(r.s3_key),
                original_filename=r.original_filename,
                mime_type=r.mime_type,
                size_bytes=r.size_bytes,
                width=r.width,
                height=r.height,
                created_at=r.created_at,
            )
            for r in rows
        ]
        return MediaAssetListResponse(data=data, total=total)
