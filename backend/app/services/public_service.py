"""Public service — cities, doctors catalog, events, articles (guest access)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from redis.asyncio import Redis
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import NotFoundError
from app.services import file_service
from app.models.cities import City
from app.services.content_block_service import list_blocks_for_entity
from app.models.content import Article, ArticleTheme, ArticleThemeAssignment
from app.models.events import Event, EventGallery
from app.models.profiles import DoctorProfile, Specialization
from app.models.subscriptions import Subscription
from app.schemas.public import (
    ArticleDetailResponse,
    ArticleListItem,
    ArticleThemeResponse,
    CityResponse,
    CityWithDoctorsResponse,
    ContentBlockPublicNested,
    DoctorPublicDetailResponse,
    DoctorPublicListItem,
    EventPublicDetailResponse,
    EventPublicListItem,
    GalleryPublicNested,
    PreviewPhotoNested,
    RecordingPublicNested,
    SeoNested,
    TariffPublicNested,
    ThemeNested,
)

logger = structlog.get_logger(__name__)

CITIES_CACHE_TTL = 300


def _has_active_subscription() -> Any:
    """Correlated EXISTS subquery: doctor has at least one active subscription."""
    return (
        select(Subscription.id)
        .where(
            Subscription.user_id == DoctorProfile.user_id,
            Subscription.status == "active",
            or_(
                Subscription.ends_at.is_(None),
                Subscription.ends_at > func.now(),
            ),
        )
        .correlate(DoctorProfile)
        .exists()
    )


class PublicService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:  # type: ignore[type-arg]
        self.db = db
        self.redis = redis

    # ── Cities ────────────────────────────────────────────────────

    async def list_cities(
        self, *, with_doctors: bool = False
    ) -> dict[str, Any]:
        cache_key = f"cache:cities:{with_doctors}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        if with_doctors:
            items = await self._cities_with_doctors()
        else:
            items = await self._cities_plain()

        result: dict[str, Any] = {"data": items}
        await self.redis.set(cache_key, json.dumps(result, default=str), ex=CITIES_CACHE_TTL)
        return result

    async def _cities_plain(self) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(City)
                .where(City.is_active.is_(True))
                .order_by(City.name)
            )
        ).scalars().all()
        return [
            CityResponse(id=c.id, name=c.name, slug=c.slug).model_dump(mode="json")
            for c in rows
        ]

    async def _cities_with_doctors(self) -> list[dict[str, Any]]:
        doctor_count = (
            func.count(DoctorProfile.id)
            .filter(
                DoctorProfile.status == "active",
                _has_active_subscription(),
            )
            .label("doctors_count")
        )
        q = (
            select(City.id, City.name, City.slug, doctor_count)
            .outerjoin(DoctorProfile, DoctorProfile.city_id == City.id)
            .where(City.is_active.is_(True))
            .group_by(City.id)
            .having(doctor_count > 0)
            .order_by(City.name)
        )
        rows = (await self.db.execute(q)).all()
        return [
            CityWithDoctorsResponse(
                id=r.id, name=r.name, slug=r.slug, doctors_count=r.doctors_count
            ).model_dump(mode="json")
            for r in rows
        ]

    async def get_city(self, slug: str) -> CityWithDoctorsResponse:
        doctor_count = (
            func.count(DoctorProfile.id)
            .filter(
                DoctorProfile.status == "active",
                _has_active_subscription(),
            )
            .label("doctors_count")
        )
        q = (
            select(City.id, City.name, City.slug, doctor_count)
            .outerjoin(DoctorProfile, DoctorProfile.city_id == City.id)
            .where(and_(City.is_active.is_(True), City.slug == slug))
            .group_by(City.id)
        )
        row = (await self.db.execute(q)).one_or_none()
        if not row:
            raise NotFoundError("City not found")
        return CityWithDoctorsResponse(
            id=row.id, name=row.name, slug=row.slug, doctors_count=row.doctors_count
        )

    # ── Doctors (public catalog) ──────────────────────────────────

    async def list_doctors(
        self,
        *,
        limit: int = 12,
        offset: int = 0,
        city_id: UUID | None = None,
        city_slug: str | None = None,
        specialization: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        active_sub = _has_active_subscription()
        base = (
            select(DoctorProfile)
            .options(
                joinedload(DoctorProfile.city),
                joinedload(DoctorProfile.specialization),
            )
            .where(DoctorProfile.status == "active", active_sub)
        )
        count_q = select(func.count(DoctorProfile.id)).where(
            DoctorProfile.status == "active", active_sub
        )

        filters: list[Any] = []

        if city_slug and not city_id:
            city_result = await self.db.execute(
                select(City.id).where(City.slug == city_slug)
            )
            resolved = city_result.scalar_one_or_none()
            if resolved:
                city_id = resolved

        if city_id:
            filters.append(DoctorProfile.city_id == city_id)
        if specialization:
            base = base.join(
                Specialization,
                DoctorProfile.specialization_id == Specialization.id,
                isouter=True,
            )
            count_q = count_q.join(
                Specialization,
                DoctorProfile.specialization_id == Specialization.id,
                isouter=True,
            )
            filters.append(Specialization.name.ilike(f"%{specialization}%"))
        if search and len(search) >= 2:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    DoctorProfile.last_name.ilike(pattern),
                    DoctorProfile.first_name.ilike(pattern),
                )
            )

        if filters:
            base = base.where(and_(*filters))
            count_q = count_q.where(and_(*filters))

        total = (await self.db.execute(count_q)).scalar() or 0

        base = base.order_by(DoctorProfile.last_name, DoctorProfile.first_name)
        base = base.offset(offset).limit(limit)

        rows = (await self.db.execute(base)).unique().scalars().all()

        items = [self._doctor_to_list_item(dp) for dp in rows]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    def _doctor_to_list_item(self, dp: DoctorProfile) -> DoctorPublicListItem:
        return DoctorPublicListItem(
            id=dp.id,
            first_name=dp.first_name,
            last_name=dp.last_name,
            middle_name=dp.middle_name,
            city=dp.city.name if dp.city else None,
            clinic_name=dp.clinic_name,
            specialization=dp.specialization.name if dp.specialization else None,
            academic_degree=dp.academic_degree,
            bio=dp.bio,
            photo_url=file_service.build_media_url(dp.photo_url),
            public_phone=dp.public_phone,
            public_email=dp.public_email,
            slug=dp.slug,
        )

    async def get_doctor(self, identifier: str) -> DoctorPublicDetailResponse:
        try:
            uid = UUID(identifier)
            id_filter = DoctorProfile.id == uid
        except (ValueError, AttributeError):
            id_filter = DoctorProfile.slug == identifier

        result = await self.db.execute(
            select(DoctorProfile)
            .options(
                joinedload(DoctorProfile.city),
                joinedload(DoctorProfile.specialization),
            )
            .where(
                and_(
                    id_filter,
                    DoctorProfile.status == "active",
                    _has_active_subscription(),
                )
            )
        )
        dp = result.unique().scalar_one_or_none()
        if not dp:
            raise NotFoundError("Doctor not found")

        city_name = dp.city.name if dp.city else None
        full_name = f"{dp.last_name} {dp.first_name}"
        if dp.middle_name:
            full_name += f" {dp.middle_name}"

        seo = SeoNested(
            title=f"{full_name} — врач-трихолог{f' в г. {city_name}' if city_name else ''} | РОТА",
            description=f"Публичный профиль врача-трихолога {full_name}.{f' {dp.clinic_name}, {city_name}.' if dp.clinic_name and city_name else ''}",
            og_type="profile",
            og_image=file_service.build_media_url(dp.photo_url),
            twitter_card="summary_large_image",
        )

        blocks = await list_blocks_for_entity(self.db, "doctor_profile", dp.id)
        content_blocks = [
            ContentBlockPublicNested(
                id=str(b.id),
                block_type=b.block_type,
                sort_order=b.sort_order,
                title=b.title,
                content=b.content,
                media_url=file_service.build_media_url(b.media_url),
                thumbnail_url=file_service.build_media_url(b.thumbnail_url),
                link_url=b.link_url,
                link_label=b.link_label,
                device_type=b.device_type,
            )
            for b in blocks
        ]

        return DoctorPublicDetailResponse(
            id=dp.id,
            first_name=dp.first_name,
            last_name=dp.last_name,
            middle_name=dp.middle_name,
            city=city_name,
            clinic_name=dp.clinic_name,
            position=dp.position,
            specialization=dp.specialization.name if dp.specialization else None,
            academic_degree=dp.academic_degree,
            bio=dp.bio,
            photo_url=file_service.build_media_url(dp.photo_url),
            public_phone=dp.public_phone,
            public_email=dp.public_email,
            slug=dp.slug,
            seo=seo,
            content_blocks=content_blocks,
        )

    # ── Events ────────────────────────────────────────────────────

    async def list_events(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        period: str = "upcoming",
    ) -> dict[str, Any]:
        base = (
            select(Event)
            .options(selectinload(Event.tariffs))
            .where(Event.status != "cancelled")
        )
        count_q = select(func.count(Event.id)).where(Event.status != "cancelled")

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

        items = [self._event_to_list_item(ev) for ev in rows]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    def _event_to_list_item(self, ev: Event) -> EventPublicListItem:
        tariffs = [
            TariffPublicNested(
                id=t.id,
                name=t.name,
                description=t.description,
                conditions=t.conditions,
                details=t.details,
                price=float(t.price),
                member_price=float(t.member_price),
                benefits=t.benefits if isinstance(t.benefits, list) else [],
                seats_limit=t.seats_limit,
                seats_available=(t.seats_limit - t.seats_taken) if t.seats_limit else None,
            )
            for t in ev.tariffs
            if t.is_active
        ]
        return EventPublicListItem(
            id=ev.id,
            title=ev.title,
            slug=ev.slug,
            description=ev.description,
            event_date=ev.event_date,
            event_end_date=ev.event_end_date,
            location=ev.location,
            cover_image_url=file_service.build_media_url(ev.cover_image_url),
            tariffs=tariffs,
            status=ev.status,
        )

    async def get_event(self, slug: str) -> EventPublicDetailResponse:
        result = await self.db.execute(
            select(Event)
            .options(
                selectinload(Event.tariffs),
                selectinload(Event.galleries).selectinload(EventGallery.photos),
                selectinload(Event.recordings),
            )
            .where(and_(Event.slug == slug, Event.status != "cancelled"))
        )
        ev = result.unique().scalar_one_or_none()
        if not ev:
            raise NotFoundError("Event not found")

        tariffs = [
            TariffPublicNested(
                id=t.id,
                name=t.name,
                description=t.description,
                conditions=t.conditions,
                details=t.details,
                price=float(t.price),
                member_price=float(t.member_price),
                benefits=t.benefits if isinstance(t.benefits, list) else [],
                seats_limit=t.seats_limit,
                seats_available=(t.seats_limit - t.seats_taken) if t.seats_limit else None,
            )
            for t in ev.tariffs
            if t.is_active
        ]

        galleries = [
            GalleryPublicNested(
                id=g.id,
                title=g.title,
                access_level=g.access_level,
                photos_count=len(g.photos),
                preview_photos=[
                    PreviewPhotoNested(thumbnail_url=file_service.build_media_url(p.thumbnail_url))
                    for p in g.photos[:4]
                ],
            )
            for g in ev.galleries
            if g.access_level == "public"
        ]

        recordings = [
            RecordingPublicNested(
                id=r.id,
                title=r.title,
                video_source=r.video_source,
                duration_seconds=r.duration_seconds,
                access_level=r.access_level,
            )
            for r in ev.recordings
            if r.status != "hidden"
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
                id=str(b.id),
                block_type=b.block_type,
                sort_order=b.sort_order,
                title=b.title,
                content=b.content,
                media_url=file_service.build_media_url(b.media_url),
                thumbnail_url=file_service.build_media_url(b.thumbnail_url),
                link_url=b.link_url,
                link_label=b.link_label,
                device_type=b.device_type,
            )
            for b in blocks
        ]

        return EventPublicDetailResponse(
            id=ev.id,
            title=ev.title,
            slug=ev.slug,
            description=ev.description,
            event_date=ev.event_date,
            event_end_date=ev.event_end_date,
            location=ev.location,
            cover_image_url=file_service.build_media_url(ev.cover_image_url),
            tariffs=tariffs,
            galleries=galleries,
            recordings=recordings,
            seo=seo,
            content_blocks=content_blocks,
        )

    # ── Articles ──────────────────────────────────────────────────

    async def list_articles(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        theme_slug: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        base = (
            select(Article)
            .options(selectinload(Article.theme_assignments).joinedload(ArticleThemeAssignment.theme))
            .where(Article.status == "published")
        )
        count_q = select(func.count(Article.id)).where(Article.status == "published")

        if theme_slug:
            base = base.join(ArticleThemeAssignment).join(ArticleTheme).where(
                ArticleTheme.slug == theme_slug
            )
            count_q = count_q.join(ArticleThemeAssignment).join(ArticleTheme).where(
                ArticleTheme.slug == theme_slug
            )
        if search and len(search) >= 2:
            base = base.where(Article.title.ilike(f"%{search}%"))
            count_q = count_q.where(Article.title.ilike(f"%{search}%"))

        total = (await self.db.execute(count_q)).scalar() or 0

        base = base.order_by(Article.published_at.desc())
        base = base.offset(offset).limit(limit)

        rows = (await self.db.execute(base)).unique().scalars().all()

        items = [
            ArticleListItem(
                id=a.id,
                slug=a.slug,
                title=a.title,
                excerpt=a.excerpt,
                cover_image_url=file_service.build_media_url(a.cover_image_url),
                published_at=a.published_at,
                themes=[
                    ThemeNested(id=ta.theme.id, slug=ta.theme.slug, title=ta.theme.title)
                    for ta in a.theme_assignments
                ],
            )
            for a in rows
        ]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    async def list_article_themes(
        self, *, active: bool | None = None, has_articles: bool | None = None
    ) -> dict[str, Any]:
        base = select(ArticleTheme)

        if active is True:
            base = base.where(ArticleTheme.is_active.is_(True))
        elif active is False:
            base = base.where(ArticleTheme.is_active.is_(False))

        if has_articles is True:
            published_article_exists = exists(
                select(ArticleThemeAssignment.id)
                .join(Article, ArticleThemeAssignment.article_id == Article.id)
                .where(
                    and_(
                        ArticleThemeAssignment.theme_id == ArticleTheme.id,
                        Article.status == "published",
                    )
                )
            )
            base = base.where(published_article_exists)

        base = base.order_by(ArticleTheme.sort_order, ArticleTheme.title)
        rows = (await self.db.execute(base)).scalars().all()

        items = [
            ArticleThemeResponse(id=t.id, slug=t.slug, title=t.title)
            for t in rows
        ]
        return {"data": items}

    async def get_article(self, slug: str) -> ArticleDetailResponse:
        result = await self.db.execute(
            select(Article)
            .options(selectinload(Article.theme_assignments).joinedload(ArticleThemeAssignment.theme))
            .where(and_(Article.slug == slug, Article.status == "published"))
        )
        article = result.unique().scalar_one_or_none()
        if not article:
            raise NotFoundError("Article not found")

        seo_title = article.seo_title or f"{article.title} | РОТА"
        seo_desc = article.seo_description or article.excerpt or article.title

        seo = SeoNested(
            title=seo_title,
            description=seo_desc,
            og_type="article",
            og_image=file_service.build_media_url(article.cover_image_url),
            twitter_card="summary_large_image",
        )

        blocks = await list_blocks_for_entity(self.db, "article", article.id)
        content_blocks = [
            ContentBlockPublicNested(
                id=str(b.id),
                block_type=b.block_type,
                sort_order=b.sort_order,
                title=b.title,
                content=b.content,
                media_url=file_service.build_media_url(b.media_url),
                thumbnail_url=file_service.build_media_url(b.thumbnail_url),
                link_url=b.link_url,
                link_label=b.link_label,
                device_type=b.device_type,
            )
            for b in blocks
        ]

        return ArticleDetailResponse(
            id=article.id,
            slug=article.slug,
            title=article.title,
            content=article.content,
            excerpt=article.excerpt,
            cover_image_url=file_service.build_media_url(article.cover_image_url),
            published_at=article.published_at,
            themes=[
                ThemeNested(id=ta.theme.id, slug=ta.theme.slug, title=ta.theme.title)
                for ta in article.theme_assignments
            ],
            seo=seo,
            content_blocks=content_blocks,
        )
