"""Core admin CRUD for events — list, create, detail, update, delete."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import UploadFile
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.admin_filters import normalize_msk_day_range
from app.core.enums import EventRegistrationStatus, EventStatus
from app.core.exceptions import AppValidationError, NotFoundError
from app.core.utils import generate_unique_slug
from app.models.events import (
    Event,
    EventGallery,
    EventRegistration,
)
from app.schemas.events_admin import (
    EventCreatedResponse,
    EventDetailResponse,
    EventListItem,
    GalleryNested,
    RecordingNested,
    TariffNested,
)
from app.schemas.shared import block_to_nested
from app.services import file_service
from app.services.content_block_service import list_blocks_for_entity

logger = structlog.get_logger(__name__)
class EventsAdminCore:
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
                        EventRegistration.status == EventRegistrationStatus.CONFIRMED,
                    )
                ),
                0,
            ).label("revenue")
        )

        base = (
            select(Event, reg_count, revenue)
            .outerjoin(EventRegistration, EventRegistration.event_id == Event.id)
            .group_by(Event.id)
        )
        count_q = select(func.count(Event.id))

        filters: list[Any] = []
        if status:
            filters.append(Event.status == status)
        lo, hi = normalize_msk_day_range(date_from, date_to)
        if lo is not None:
            filters.append(Event.event_date >= lo)
        if hi is not None:
            filters.append(Event.event_date < hi)

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
                id=ev.id, title=ev.title, slug=ev.slug,
                event_date=ev.event_date, event_end_date=ev.event_end_date,
                location=ev.location, status=ev.status,
                registrations_count=reg_cnt, revenue=float(rev),
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
                cover_image, path="events/covers",
                allowed_types=file_service.IMAGE_MIMES, max_size_mb=5,
            )
            cover_url = key

        event = Event(
            title=title, slug=slug, description=description,
            event_date=event_date, event_end_date=event_end_date,
            location=location, status=status,
            cover_image_url=cover_url, created_by=admin_id,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        return EventCreatedResponse(
            id=event.id, title=event.title, slug=event.slug,
            status=event.status, created_at=event.created_at,
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
        content_blocks = [block_to_nested(b) for b in blocks]

        return EventDetailResponse(
            id=ev.id, title=ev.title, slug=ev.slug, description=ev.description,
            event_date=ev.event_date, event_end_date=ev.event_end_date,
            location=ev.location,
            cover_image_url=file_service.build_media_url(ev.cover_image_url),
            status=ev.status, created_by=ev.created_by, created_at=ev.created_at,
            tariffs=tariffs, galleries=galleries, recordings=recordings,
            content_blocks=content_blocks,
        )

    # ── Update ────────────────────────────────────────────────────

    async def update_event(
        self, event_id: UUID, *, data: dict[str, Any],
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
                        EventRegistration.status == EventRegistrationStatus.CONFIRMED,
                    )
                )
            )
        ).scalar() or 0

        if confirmed > 0:
            raise AppValidationError(
                "Невозможно удалить мероприятие с подтверждёнными регистрациями. "
                "Сначала отмените регистрации."
            )

        event.status = EventStatus.CANCELLED
        event.deleted_at = datetime.now(UTC)
        await self.db.commit()
