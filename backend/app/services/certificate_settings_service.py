"""Service for managing certificate generation settings (singleton row)."""

from __future__ import annotations

import structlog
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate_settings import CertificateSettings
from app.services import file_service

logger = structlog.get_logger(__name__)

_ASSET_PATH = "certificate-assets"
_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
_MAX_ASSET_MB = 2


class CertificateSettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_settings(self) -> CertificateSettings:
        result = await self.db.execute(
            select(CertificateSettings).where(CertificateSettings.id == 1)
        )
        settings = result.scalar_one_or_none()
        if not settings:
            settings = CertificateSettings(id=1)
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
        return settings

    async def update_settings(self, data: dict) -> CertificateSettings:
        settings = await self.get_settings()
        for key, value in data.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)
        await self.db.commit()
        await self.db.refresh(settings)
        logger.info("certificate_settings_updated", changed_fields=list(data.keys()))
        return settings

    async def upload_asset(
        self, field: str, upload: UploadFile
    ) -> CertificateSettings:
        s3_key = await file_service.upload_file(
            upload, _ASSET_PATH, allowed_types=_ALLOWED_IMAGE_TYPES, max_size_mb=_MAX_ASSET_MB
        )
        settings = await self.get_settings()
        old_key = getattr(settings, field, None)
        setattr(settings, field, s3_key)
        await self.db.commit()
        await self.db.refresh(settings)

        if old_key:
            try:
                await file_service.delete_file(old_key)
            except Exception:
                logger.warning("certificate_asset_delete_failed", old_key=old_key)

        logger.info("certificate_asset_uploaded", field=field, s3_key=s3_key)
        return settings

    def to_response(self, settings: CertificateSettings) -> dict:
        return {
            "id": settings.id,
            "president_full_name": settings.president_full_name,
            "president_title": settings.president_title,
            "organization_full_name": settings.organization_full_name,
            "organization_short_name": settings.organization_short_name,
            "certificate_member_text": settings.certificate_member_text,
            "logo_url": file_service.build_media_url(settings.logo_s3_key),
            "stamp_url": file_service.build_media_url(settings.stamp_s3_key),
            "signature_url": file_service.build_media_url(settings.signature_s3_key),
            "background_url": file_service.build_media_url(settings.background_s3_key),
            "certificate_number_prefix": settings.certificate_number_prefix,
            "validity_text_template": settings.validity_text_template,
            "updated_at": settings.updated_at,
        }
