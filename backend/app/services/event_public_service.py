"""Public event service — list and detail for guest access."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import EventStatus, RecordingStatus
from app.core.exceptions import NotFoundError
from app.models.events import Event, EventGallery
from app.schemas.public import (
    EventPublicDetailResponse,
    EventPublicListItem,
    GalleryPublicNested,
    PreviewPhotoNested,
    RecordingPublicNested,
    SeoNested,
    TariffPublicNested,
)
from app.schemas.shared import ContentBlockPublicNested
from app.services import file_service
from app.services.content_block_service import list_blocks_for_entity


class EventPublicService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_events(
        self, *, limit: int = 20, offset: int = 0, period: str = "upcoming",
    ) -> dict[str, Any]:
        base = (
            select(Event)
            .options(selectinload(Event.tariffs))
            .where(Event.status != EventStatus.CANCELLED)
        )
        count_q = select(func.count(Event.id)).where(Event.status != EventStatus.CANCELLED)

        now = datetime.now(UTC)
        if period == "upcoming":
            base = base.where(Event.event_date >= now)
            count_q = count_q.where(Event.event_date >= now)
            base = base.order_by(Event.event_date.asc())
        elif period == "past":
            base = base.where(Event.event_date < now)
            count_q = count_q.where(Event.event_date < now)
            base = base.order_by(Event.event_date.desc())
        else:
            base = base.order_by(Event.event_date.desc())

        total = (await self.db.execute(count_q)).scalar() or 0
        base = base.offset(offset).limit(limit)
        rows = (await self.db.execute(base)).unique().scalars().all()

        items = [self._to_list_item(ev) for ev in rows]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    def _to_list_item(self, ev: Event) -> EventPublicListItem:
        tariffs = self._build_tariffs(ev)
        return EventPublicListItem(
            id=ev.id, title=ev.title, slug=ev.slug,
            description=ev.description, event_date=ev.event_date,
            event_end_date=ev.event_end_date, location=ev.location,
            cover_image_url=file_service.build_media_url(ev.cover_image_url),
            tariffs=tariffs, status=ev.status,
        )

    async def get_event(self, slug: str) -> EventPublicDetailResponse:
        result = await self.db.execute(
            select(Event)
            .options(
                selectinload(Event.tariffs),
                selectinload(Event.galleries).selectinload(EventGallery.photos),
                selectinload(Event.recordings),
            )
            .where(and_(Event.slug == slug, Event.status != EventStatus.CANCELLED))
        )
        ev = result.unique().scalar_one_or_none()
        if not ev:
            raise NotFoundError("Event not found")

        tariffs = self._build_tariffs(ev)

        galleries = [
            GalleryPublicNested(
                id=g.id, title=g.title, access_level=g.access_level,
                photos_count=len(g.photos),
                preview_photos=[
                    PreviewPhotoNested(thumbnail_url=file_service.build_media_url(p.thumbnail_url))
                    for p in g.photos[:4]
                ],
            )
            for g in ev.galleries if g.access_level == "public"
        ]

        recordings = [
            RecordingPublicNested(
                id=r.id, title=r.title, video_source=r.video_source,
                duration_seconds=r.duration_seconds, access_level=r.access_level,
            )
            for r in ev.recordings if r.status != RecordingStatus.HIDDEN
        ]

        seo = SeoNested(
            title=f"{ev.title} | РОТА",
            description=ev.description[:160] if ev.description else None,
            og_type="event",
            og_image=file_service.build_media_url(ev.cover_image_url),
            twitter_card="summary_large_image",
        )

        blocks = await list_blocks_for_entity(self.db, "event", ev.id)
        content_blocks = [
            ContentBlockPublicNested(
                id=str(b.id), block_type=b.block_type, sort_order=b.sort_order,
                title=b.title, content=b.content,
                media_url=file_service.build_media_url(b.media_url),
                thumbnail_url=file_service.build_media_url(b.thumbnail_url),
                link_url=b.link_url, link_label=b.link_label, device_type=b.device_type,
            )
            for b in blocks
        ]

        return EventPublicDetailResponse(
            id=ev.id, title=ev.title, slug=ev.slug,
            description=ev.description, event_date=ev.event_date,
            event_end_date=ev.event_end_date, location=ev.location,
            cover_image_url=file_service.build_media_url(ev.cover_image_url),
            tariffs=tariffs, galleries=galleries, recordings=recordings,
            seo=seo, content_blocks=content_blocks,
        )

    @staticmethod
    def _build_tariffs(ev: Event) -> list[TariffPublicNested]:
        return [
            TariffPublicNested(
                id=t.id, name=t.name, description=t.description,
                conditions=t.conditions, details=t.details,
                price=float(t.price), member_price=float(t.member_price),
                benefits=t.benefits if isinstance(t.benefits, list) else [],
                seats_limit=t.seats_limit,
                seats_available=(t.seats_limit - t.seats_taken) if t.seats_limit else None,
            )
            for t in ev.tariffs if t.is_active
        ]
