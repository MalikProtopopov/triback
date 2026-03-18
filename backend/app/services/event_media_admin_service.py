"""Admin service for event galleries and recordings."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppValidationError, NotFoundError
from app.models.events import Event, EventGallery, EventGalleryPhoto, EventRecording
from app.schemas.events_admin import (
    GalleryResponse,
    PhotoNested,
    PhotoUploadResponse,
    RecordingCreateRequest,
    RecordingResponse,
    RecordingUpdateRequest,
)
from app.services import file_service

VIDEO_MIMES = {"video/mp4", "video/webm", "video/quicktime"}


class EventMediaAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Galleries ─────────────────────────────────────────────────

    async def create_gallery(
        self, event_id: UUID, data: dict[str, Any],
    ) -> GalleryResponse:
        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")

        gallery = EventGallery(event_id=event_id, **data)
        self.db.add(gallery)
        await self.db.commit()
        await self.db.refresh(gallery)

        return GalleryResponse(
            id=gallery.id, event_id=gallery.event_id,
            title=gallery.title, access_level=gallery.access_level,
            created_at=gallery.created_at,
        )

    async def upload_photos(
        self, event_id: UUID, gallery_id: UUID, files: list[UploadFile],
    ) -> PhotoUploadResponse:
        result = await self.db.execute(
            select(EventGallery).where(
                and_(EventGallery.id == gallery_id, EventGallery.event_id == event_id)
            )
        )
        gallery = result.scalar_one_or_none()
        if not gallery:
            raise NotFoundError("Gallery not found")

        if len(files) > 50:
            raise AppValidationError("Максимум 50 файлов за раз")

        photos: list[PhotoNested] = []
        for f in files:
            main_key, thumb_key = await file_service.upload_image_with_thumbnail(
                f,
                path=f"events/{event_id}/galleries/{gallery_id}",
                max_size_mb=10,
            )
            photo = EventGalleryPhoto(
                gallery_id=gallery_id,
                file_url=main_key,
                thumbnail_url=thumb_key,
                sort_order=len(photos),
            )
            self.db.add(photo)
            await self.db.flush()
            photos.append(PhotoNested(
                id=photo.id,
                file_url=file_service.build_media_url(main_key),
                thumbnail_url=file_service.build_media_url(thumb_key),
            ))

        await self.db.commit()
        return PhotoUploadResponse(uploaded=len(photos), photos=photos)

    # ── Recordings ────────────────────────────────────────────────

    async def create_recording(
        self,
        event_id: UUID,
        data: RecordingCreateRequest,
        video_file: UploadFile | None = None,
    ) -> RecordingResponse:
        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")

        rec = EventRecording(
            event_id=event_id,
            title=data.title,
            video_source=data.video_source,
            access_level=data.access_level,
            status=data.status,
            duration_seconds=data.duration_seconds,
        )

        if data.video_source == "external":
            rec.video_url = data.video_url
        elif data.video_source == "uploaded" and video_file:
            key = await file_service.upload_file(
                video_file,
                path=f"events/{event_id}/recordings",
                allowed_types=VIDEO_MIMES,
                max_size_mb=2048,
            )
            rec.video_file_key = key
            rec.video_file_size = video_file.size
            rec.video_mime_type = video_file.content_type

        self.db.add(rec)
        await self.db.commit()
        await self.db.refresh(rec)
        return await self._recording_to_response(rec)

    async def update_recording(
        self,
        event_id: UUID,
        recording_id: UUID,
        data: RecordingUpdateRequest,
        video_file: UploadFile | None = None,
    ) -> RecordingResponse:
        result = await self.db.execute(
            select(EventRecording).where(
                and_(EventRecording.id == recording_id, EventRecording.event_id == event_id)
            )
        )
        rec = result.scalar_one_or_none()
        if not rec:
            raise NotFoundError("Recording not found")

        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            if hasattr(rec, field):
                setattr(rec, field, value)

        if video_file:
            if rec.video_file_key:
                await file_service.delete_file(rec.video_file_key)
            key = await file_service.upload_file(
                video_file,
                path=f"events/{event_id}/recordings",
                allowed_types=VIDEO_MIMES,
                max_size_mb=2048,
            )
            rec.video_file_key = key
            rec.video_file_size = video_file.size
            rec.video_mime_type = video_file.content_type
            rec.video_source = "uploaded"  # type: ignore[assignment]

        await self.db.commit()
        await self.db.refresh(rec)
        return await self._recording_to_response(rec)

    @staticmethod
    async def _recording_to_response(r: EventRecording) -> RecordingResponse:
        playback_url: str | None = None
        if r.video_file_key:
            playback_url = await file_service.get_presigned_url(r.video_file_key)

        return RecordingResponse(
            id=r.id, event_id=r.event_id, title=r.title,
            video_source=r.video_source, video_url=r.video_url,
            video_playback_url=playback_url,
            video_file_size=r.video_file_size, video_mime_type=r.video_mime_type,
            duration_seconds=r.duration_seconds, access_level=r.access_level,
            status=r.status, sort_order=r.sort_order, created_at=r.created_at,
        )
