"""Admin service for events, tariffs, galleries, recordings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import UploadFile
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppValidationError, NotFoundError
from app.core.utils import generate_unique_slug
from app.models.events import (
    Event,
    EventGallery,
    EventGalleryPhoto,
    EventRecording,
    EventRegistration,
    EventTariff,
)
from app.models.profiles import DoctorProfile
from app.models.users import User
from app.schemas.content_admin import ContentBlockNested
from app.schemas.events_admin import (
    EventCreatedResponse,
    EventDetailResponse,
    EventListItem,
    GalleryNested,
    GalleryResponse,
    PhotoNested,
    PhotoUploadResponse,
    RecordingCreateRequest,
    RecordingNested,
    RecordingResponse,
    RecordingUpdateRequest,
    RegistrationListItem,
    RegistrationListResponse,
    RegistrationSummary,
    RegistrationTariffNested,
    RegistrationUserNested,
    TariffNested,
    TariffResponse,
)
from app.services import file_service
from app.services.content_block_service import list_blocks_for_entity

logger = structlog.get_logger(__name__)

VIDEO_MIMES = {"video/mp4", "video/webm", "video/quicktime"}


class EventsAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── List ──────────────────────────────────────────────────────

    async def list_events(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "event_date",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        reg_count = (
            func.count(EventRegistration.id)
            .filter(EventRegistration.event_id == Event.id)
            .label("registrations_count")
        )
        revenue = (
            func.coalesce(
                func.sum(EventRegistration.applied_price).filter(
                    and_(
                        EventRegistration.event_id == Event.id,
                        EventRegistration.status == "confirmed",
                    )
                ),
                0,
            )
            .label("revenue")
        )

        base = select(
            Event, reg_count, revenue
        ).outerjoin(EventRegistration, EventRegistration.event_id == Event.id).group_by(Event.id)

        count_q = select(func.count(Event.id))

        filters: list[Any] = []
        if status:
            filters.append(Event.status == status)
        if date_from:
            filters.append(Event.event_date >= date_from)
        if date_to:
            filters.append(Event.event_date <= date_to)

        if filters:
            base = base.where(and_(*filters))
            count_q = count_q.where(and_(*filters))

        total = (await self.db.execute(count_q)).scalar() or 0

        sort_col = getattr(Event, sort_by, Event.event_date)
        base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
        base = base.offset(offset).limit(limit)

        rows = (await self.db.execute(base)).all()

        items = [
            EventListItem(
                id=ev.id,
                title=ev.title,
                slug=ev.slug,
                event_date=ev.event_date,
                event_end_date=ev.event_end_date,
                location=ev.location,
                status=ev.status,
                registrations_count=reg_cnt,
                revenue=float(rev),
                cover_image_url=file_service.build_media_url(ev.cover_image_url),
            )
            for ev, reg_cnt, rev in rows
        ]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    # ── Create ────────────────────────────────────────────────────

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
        slug = slug or await generate_unique_slug(self.db, Event, title)

        cover_url: str | None = None
        if cover_image:
            key = await file_service.upload_file(
                cover_image,
                path="events/covers",
                allowed_types=file_service.IMAGE_MIMES,
                max_size_mb=5,
            )
            cover_url = key

        event = Event(
            title=title,
            slug=slug,
            description=description,
            event_date=event_date,
            event_end_date=event_end_date,
            location=location,
            status=status,
            cover_image_url=cover_url,
            created_by=admin_id,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        return EventCreatedResponse(
            id=event.id,
            title=event.title,
            slug=event.slug,
            status=event.status,
            created_at=event.created_at,
        )

    # ── Detail ────────────────────────────────────────────────────

    async def get_event(self, event_id: UUID) -> EventDetailResponse:
        result = await self.db.execute(
            select(Event)
            .options(
                selectinload(Event.tariffs),
                selectinload(Event.galleries).selectinload(EventGallery.photos),
                selectinload(Event.recordings),
            )
            .where(Event.id == event_id)
        )
        ev = result.unique().scalar_one_or_none()
        if not ev:
            raise NotFoundError("Event not found")

        tariffs = [
            TariffNested(
                id=t.id, name=t.name, description=t.description,
                conditions=t.conditions, details=t.details,
                price=float(t.price), member_price=float(t.member_price),
                benefits=t.benefits if isinstance(t.benefits, list) else [],
                seats_limit=t.seats_limit, seats_taken=t.seats_taken,
                is_active=t.is_active, sort_order=t.sort_order,
            )
            for t in ev.tariffs
        ]
        galleries = [
            GalleryNested(
                id=g.id, title=g.title, access_level=g.access_level,
                photos_count=len(g.photos), created_at=g.created_at,
            )
            for g in ev.galleries
        ]
        recordings = [
            RecordingNested(
                id=r.id, title=r.title, video_source=r.video_source,
                video_url=r.video_url, duration_seconds=r.duration_seconds,
                access_level=r.access_level, status=r.status,
                sort_order=r.sort_order, created_at=r.created_at,
                video_file_size=r.video_file_size, video_mime_type=r.video_mime_type,
            )
            for r in ev.recordings
        ]

        blocks = await list_blocks_for_entity(self.db, "event", ev.id)
        content_blocks = [
            ContentBlockNested(
                id=b.id,
                block_type=b.block_type,
                sort_order=b.sort_order,
                title=b.title,
                content=b.content,
                media_url=file_service.build_media_url(b.media_url),
                thumbnail_url=file_service.build_media_url(b.thumbnail_url),
                link_url=b.link_url,
                link_label=b.link_label,
                device_type=b.device_type,
                block_metadata=b.block_metadata,
            )
            for b in blocks
        ]

        return EventDetailResponse(
            id=ev.id, title=ev.title, slug=ev.slug, description=ev.description,
            event_date=ev.event_date, event_end_date=ev.event_end_date,
            location=ev.location, cover_image_url=file_service.build_media_url(ev.cover_image_url),
            status=ev.status, created_by=ev.created_by, created_at=ev.created_at,
            tariffs=tariffs, galleries=galleries, recordings=recordings,
            content_blocks=content_blocks,
        )

    # ── Update ────────────────────────────────────────────────────

    async def update_event(
        self,
        event_id: UUID,
        *,
        data: dict[str, Any],
        cover_image: UploadFile | None = None,
    ) -> EventDetailResponse:
        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")

        for field, value in data.items():
            if value is not None and hasattr(event, field):
                setattr(event, field, value)

        if cover_image:
            if event.cover_image_url:
                await file_service.delete_file(event.cover_image_url)
            key = await file_service.upload_file(
                cover_image, path="events/covers",
                allowed_types=file_service.IMAGE_MIMES, max_size_mb=5,
            )
            event.cover_image_url = key

        await self.db.commit()
        return await self.get_event(event_id)

    # ── Delete (soft) ─────────────────────────────────────────────

    async def delete_event(self, event_id: UUID) -> None:
        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")

        confirmed = (
            await self.db.execute(
                select(func.count(EventRegistration.id)).where(
                    and_(
                        EventRegistration.event_id == event_id,
                        EventRegistration.status == "confirmed",
                    )
                )
            )
        ).scalar() or 0

        if confirmed > 0:
            raise AppValidationError(
                "Невозможно удалить мероприятие с подтверждёнными регистрациями. "
                "Сначала отмените регистрации."
            )

        event.status = "cancelled"  # type: ignore[assignment]
        event.deleted_at = datetime.now(UTC)
        await self.db.commit()

    # ── Tariffs ───────────────────────────────────────────────────

    async def create_tariff(self, event_id: UUID, data: dict[str, Any]) -> TariffResponse:
        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")

        tariff = EventTariff(event_id=event_id, **data)
        self.db.add(tariff)
        await self.db.commit()
        await self.db.refresh(tariff)
        return self._tariff_to_response(tariff)

    async def update_tariff(
        self, event_id: UUID, tariff_id: UUID, data: dict[str, Any]
    ) -> TariffResponse:
        tariff = await self._get_tariff(event_id, tariff_id)

        new_limit = data.get("seats_limit")
        if new_limit is not None and new_limit < tariff.seats_taken:
            raise AppValidationError(
                f"seats_limit ({new_limit}) не может быть меньше seats_taken ({tariff.seats_taken})"
            )

        for field, value in data.items():
            if value is not None and hasattr(tariff, field):
                setattr(tariff, field, value)

        await self.db.commit()
        await self.db.refresh(tariff)
        return self._tariff_to_response(tariff)

    async def delete_tariff(self, event_id: UUID, tariff_id: UUID) -> None:
        tariff = await self._get_tariff(event_id, tariff_id)

        reg_count = (
            await self.db.execute(
                select(func.count(EventRegistration.id)).where(
                    EventRegistration.event_tariff_id == tariff_id
                )
            )
        ).scalar() or 0

        if reg_count > 0:
            raise AppValidationError("Невозможно удалить тариф с привязанными регистрациями")

        await self.db.delete(tariff)
        await self.db.commit()

    async def _get_tariff(self, event_id: UUID, tariff_id: UUID) -> EventTariff:
        result = await self.db.execute(
            select(EventTariff).where(
                and_(EventTariff.id == tariff_id, EventTariff.event_id == event_id)
            )
        )
        tariff = result.scalar_one_or_none()
        if not tariff:
            raise NotFoundError("Tariff not found")
        return tariff

    def _tariff_to_response(self, t: EventTariff) -> TariffResponse:
        return TariffResponse(
            id=t.id, event_id=t.event_id, name=t.name,
            description=t.description, conditions=t.conditions, details=t.details,
            price=float(t.price), member_price=float(t.member_price),
            benefits=t.benefits if isinstance(t.benefits, list) else [],
            seats_limit=t.seats_limit, seats_taken=t.seats_taken,
            is_active=t.is_active, sort_order=t.sort_order,
            created_at=t.created_at,
        )

    # ── Registrations ─────────────────────────────────────────────

    async def list_registrations(
        self,
        event_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> RegistrationListResponse:
        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")

        base = (
            select(EventRegistration)
            .where(EventRegistration.event_id == event_id)
        )
        count_q = select(func.count(EventRegistration.id)).where(
            EventRegistration.event_id == event_id
        )

        if status:
            base = base.where(EventRegistration.status == status)
            count_q = count_q.where(EventRegistration.status == status)

        total = (await self.db.execute(count_q)).scalar() or 0
        base = base.order_by(EventRegistration.created_at.desc())
        base = base.offset(offset).limit(limit)

        regs = (await self.db.execute(base)).scalars().all()

        reg_user_ids = list({r.user_id for r in regs})
        reg_tariff_ids = list({r.event_tariff_id for r in regs})

        user_email_map: dict[UUID, str] = {}
        dp_name_map: dict[UUID, str] = {}
        tariff_map: dict[UUID, tuple[UUID, str]] = {}

        if reg_user_ids:
            u_q = await self.db.execute(
                select(User.id, User.email).where(User.id.in_(reg_user_ids))
            )
            for uid, email in u_q.all():
                user_email_map[uid] = email
            dp_q = await self.db.execute(
                select(DoctorProfile.user_id, DoctorProfile.first_name, DoctorProfile.last_name)
                .where(DoctorProfile.user_id.in_(reg_user_ids))
            )
            for uid, fn, ln in dp_q.all():
                dp_name_map[uid] = f"{ln} {fn}"

        if reg_tariff_ids:
            t_q = await self.db.execute(
                select(EventTariff.id, EventTariff.name).where(EventTariff.id.in_(reg_tariff_ids))
            )
            for tid, tname in t_q.all():
                tariff_map[tid] = (tid, tname)

        items: list[RegistrationListItem] = []
        for r in regs:
            t_info = tariff_map.get(r.event_tariff_id)
            items.append(
                RegistrationListItem(
                    id=r.id,
                    user=RegistrationUserNested(
                        id=r.user_id,
                        email=user_email_map.get(r.user_id, ""),
                        full_name=dp_name_map.get(r.user_id),
                    ),
                    tariff=RegistrationTariffNested(
                        id=t_info[0] if t_info else r.event_tariff_id,
                        name=t_info[1] if t_info else "",
                    ),
                    applied_price=float(r.applied_price),
                    is_member_price=r.is_member_price,
                    status=r.status,
                    created_at=r.created_at,
                )
            )

        summary_q = select(
            func.count(EventRegistration.id).label("total_registrations"),
            func.count(EventRegistration.id).filter(EventRegistration.status == "confirmed").label("confirmed"),
            func.count(EventRegistration.id).filter(EventRegistration.status == "pending").label("pending"),
            func.count(EventRegistration.id).filter(EventRegistration.status == "cancelled").label("cancelled"),
            func.coalesce(
                func.sum(EventRegistration.applied_price).filter(EventRegistration.status == "confirmed"), 0
            ).label("total_revenue"),
        ).where(EventRegistration.event_id == event_id)
        s = (await self.db.execute(summary_q)).one()

        return RegistrationListResponse(
            data=items,
            summary=RegistrationSummary(
                total_registrations=s.total_registrations,
                confirmed=s.confirmed,
                pending=s.pending,
                cancelled=s.cancelled,
                total_revenue=float(s.total_revenue),
            ),
            total=total,
            limit=limit,
            offset=offset,
        )

    # ── Galleries ─────────────────────────────────────────────────

    async def create_gallery(self, event_id: UUID, data: dict[str, Any]) -> GalleryResponse:
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
        self, event_id: UUID, gallery_id: UUID, files: list[UploadFile]
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
            photos.append(PhotoNested(id=photo.id, file_url=file_service.build_media_url(main_key), thumbnail_url=file_service.build_media_url(thumb_key)))

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

    async def _recording_to_response(self, r: EventRecording) -> RecordingResponse:
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
