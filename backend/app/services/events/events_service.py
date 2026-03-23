"""Admin service for events — facade over core, registrations, tariffs, media."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.events_admin import (
    EventCreatedResponse,
    EventDetailResponse,
    GalleryResponse,
    PhotoUploadResponse,
    RecordingCreateRequest,
    RecordingResponse,
    RecordingUpdateRequest,
    RegistrationListResponse,
    TariffResponse,
)
from app.services.event_media_admin_service import EventMediaAdminService
from app.services.event_tariff_service import EventTariffService
from app.services.events.events_admin_core import EventsAdminCore
from app.services.events.events_admin_registrations import EventsAdminRegistrations


class EventsAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._core = EventsAdminCore(db)
        self._regs = EventsAdminRegistrations(db)
        self._tariffs = EventTariffService(db)
        self._media = EventMediaAdminService(db)

    async def list_events(self, **kwargs: Any) -> dict[str, Any]:
        return await self._core.list_events(**kwargs)

    async def create_event(
        self,
        admin_id: UUID,
        *,
        title: str,
        slug: str | None = None,
        description: str | None = None,
        event_date: datetime,
        event_end_date: datetime | None = None,
        location: str | None = None,
        status: str = "upcoming",
        cover_image: UploadFile | None = None,
    ) -> EventCreatedResponse:
        return await self._core.create_event(
            admin_id,
            title=title,
            slug=slug,
            description=description,
            event_date=event_date,
            event_end_date=event_end_date,
            location=location,
            status=status,
            cover_image=cover_image,
        )

    async def get_event(self, event_id: UUID) -> EventDetailResponse:
        return await self._core.get_event(event_id)

    async def update_event(
        self,
        event_id: UUID,
        *,
        data: dict[str, Any],
        cover_image: UploadFile | None = None,
    ) -> EventDetailResponse:
        return await self._core.update_event(
            event_id, data=data, cover_image=cover_image
        )

    async def delete_event(self, event_id: UUID) -> None:
        return await self._core.delete_event(event_id)

    async def list_registrations(
        self,
        event_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> RegistrationListResponse:
        return await self._regs.list_registrations(
            event_id, limit=limit, offset=offset, status=status
        )

    async def create_tariff(self, event_id: UUID, data: dict[str, Any]) -> TariffResponse:
        return await self._tariffs.create(event_id, data)

    async def update_tariff(
        self,
        event_id: UUID,
        tariff_id: UUID,
        data: dict[str, Any],
    ) -> TariffResponse:
        return await self._tariffs.update(event_id, tariff_id, data)

    async def delete_tariff(self, event_id: UUID, tariff_id: UUID) -> None:
        return await self._tariffs.delete(event_id, tariff_id)

    async def create_gallery(
        self, event_id: UUID, data: dict[str, Any]
    ) -> GalleryResponse:
        return await self._media.create_gallery(event_id, data)

    async def upload_photos(
        self,
        event_id: UUID,
        gallery_id: UUID,
        files: list[UploadFile],
    ) -> PhotoUploadResponse:
        return await self._media.upload_photos(event_id, gallery_id, files)

    async def create_recording(
        self,
        event_id: UUID,
        data: RecordingCreateRequest,
        video_file: UploadFile | None = None,
    ) -> RecordingResponse:
        return await self._media.create_recording(event_id, data, video_file)

    async def update_recording(
        self,
        event_id: UUID,
        recording_id: UUID,
        data: RecordingUpdateRequest,
        video_file: UploadFile | None = None,
    ) -> RecordingResponse:
        return await self._media.update_recording(
            event_id, recording_id, data, video_file
        )
