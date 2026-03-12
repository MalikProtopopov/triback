"""Public (guest) endpoints — no authentication required."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_optional_user_id
from app.core.pagination import PaginatedResponse
from app.core.redis import get_redis
from app.schemas.event_registration import (
    ConfirmGuestRegistrationRequest,
    RegisterForEventRequest,
    RegisterForEventResponse,
)
from app.schemas.public import (
    ArticleDetailResponse,
    ArticleListItem,
    DoctorPublicDetailResponse,
    DoctorPublicListItem,
    EventPublicDetailResponse,
    EventPublicListItem,
)
from app.services.public_service import PublicService

router = APIRouter()


# ── Cities ────────────────────────────────────────────────────────

@router.get("/cities")
async def list_cities(
    with_doctors: bool = Query(False),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> dict:
    svc = PublicService(db, redis)
    return await svc.list_cities(with_doctors=with_doctors)


# ── Doctors (public catalog) ─────────────────────────────────────

@router.get("/doctors", response_model=PaginatedResponse[DoctorPublicListItem])
async def list_doctors(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    limit: int = Query(12, ge=1, le=50),
    offset: int = Query(0, ge=0),
    city_id: UUID | None = Query(None),
    city_slug: str | None = Query(None),
    specialization: str | None = Query(None),
    search: str | None = Query(None, min_length=2),
) -> dict:
    svc = PublicService(db, redis)
    return await svc.list_doctors(
        limit=limit,
        offset=offset,
        city_id=city_id,
        city_slug=city_slug,
        specialization=specialization,
        search=search,
    )


@router.get("/doctors/{profile_id}", response_model=DoctorPublicDetailResponse)
async def get_doctor(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> DoctorPublicDetailResponse:
    svc = PublicService(db, redis)
    return await svc.get_doctor(profile_id)


# ── Events ────────────────────────────────────────────────────────

@router.get("/events", response_model=PaginatedResponse[EventPublicListItem])
async def list_events(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    period: str = Query("upcoming"),
) -> dict:
    svc = PublicService(db, redis)
    return await svc.list_events(limit=limit, offset=offset, period=period)


@router.get("/events/{slug}", response_model=EventPublicDetailResponse)
async def get_event(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> EventPublicDetailResponse:
    svc = PublicService(db, redis)
    return await svc.get_event(slug)


@router.post("/events/{event_id}/register", response_model=RegisterForEventResponse, status_code=201)
async def register_for_event(
    event_id: UUID,
    body: RegisterForEventRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    user_id: UUID | None = Depends(get_optional_user_id),
) -> RegisterForEventResponse:
    from app.services.event_registration_service import EventRegistrationService

    svc = EventRegistrationService(db, redis)
    return await svc.register(event_id, user_id, body)


@router.post(
    "/events/{event_id}/confirm-guest-registration",
    response_model=RegisterForEventResponse,
    status_code=201,
)
async def confirm_guest_registration(
    event_id: UUID,
    body: ConfirmGuestRegistrationRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> RegisterForEventResponse:
    from app.services.event_registration_service import EventRegistrationService

    svc = EventRegistrationService(db, redis)
    return await svc.confirm_guest_registration(event_id, body)


# ── Event Galleries (D18) ────────────────────────────────────────

@router.get("/events/{event_id}/galleries")
async def list_event_galleries(
    event_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID | None = Depends(get_optional_user_id),
) -> dict:
    from sqlalchemy import select

    from app.models.events import Event, EventGallery, EventGalleryPhoto, EventRegistration
    from app.models.subscriptions import Subscription

    event = await db.get(Event, event_id)
    if not event:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Event not found")

    has_access = False
    if user_id:
        sub = (await db.execute(
            select(Subscription.id).where(
                Subscription.user_id == user_id, Subscription.status == "active"
            ).limit(1)
        )).scalar_one_or_none()
        reg = (await db.execute(
            select(EventRegistration.id).where(
                EventRegistration.user_id == user_id,
                EventRegistration.event_id == event_id,
                EventRegistration.status == "confirmed",
            ).limit(1)
        )).scalar_one_or_none()
        has_access = sub is not None or reg is not None

    galleries_q = select(EventGallery).where(EventGallery.event_id == event_id).order_by(EventGallery.sort_order)
    galleries = (await db.execute(galleries_q)).scalars().all()

    items = []
    for g in galleries:
        if g.access_level == "members_only" and not has_access:
            continue
        photos = (await db.execute(
            select(EventGalleryPhoto)
            .where(EventGalleryPhoto.gallery_id == g.id)
            .order_by(EventGalleryPhoto.sort_order)
        )).scalars().all()
        items.append({
            "id": str(g.id),
            "title": g.title,
            "access_level": g.access_level,
            "photos": [
                {"id": str(p.id), "file_url": p.file_url, "thumbnail_url": p.thumbnail_url, "caption": p.caption}
                for p in photos
            ],
        })
    return {"data": items}


@router.get("/events/{event_id}/recordings")
async def list_event_recordings(
    event_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID | None = Depends(get_optional_user_id),
) -> dict:
    from sqlalchemy import select

    from app.models.events import Event, EventRecording, EventRegistration
    from app.models.subscriptions import Subscription

    event = await db.get(Event, event_id)
    if not event:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Event not found")

    has_access = False
    if user_id:
        sub = (await db.execute(
            select(Subscription.id).where(
                Subscription.user_id == user_id, Subscription.status == "active"
            ).limit(1)
        )).scalar_one_or_none()
        reg = (await db.execute(
            select(EventRegistration.id).where(
                EventRegistration.user_id == user_id,
                EventRegistration.event_id == event_id,
                EventRegistration.status == "confirmed",
            ).limit(1)
        )).scalar_one_or_none()
        has_access = sub is not None or reg is not None

    recs = (await db.execute(
        select(EventRecording).where(
            EventRecording.event_id == event_id,
            EventRecording.status == "published",
        ).order_by(EventRecording.sort_order)
    )).scalars().all()

    items = []
    for r in recs:
        if r.access_level in ("members_only", "participants_only") and not has_access:
            continue
        items.append({
            "id": str(r.id),
            "title": r.title,
            "video_source": r.video_source,
            "video_url": r.video_url,
            "duration_seconds": r.duration_seconds,
            "access_level": r.access_level,
        })
    return {"data": items}


# ── Articles ──────────────────────────────────────────────────────

@router.get("/articles", response_model=PaginatedResponse[ArticleListItem])
async def list_articles(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    theme_slug: str | None = Query(None),
    search: str | None = Query(None, min_length=2),
) -> dict:
    svc = PublicService(db, redis)
    return await svc.list_articles(
        limit=limit, offset=offset, theme_slug=theme_slug, search=search
    )


@router.get("/article-themes")
async def list_article_themes(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    active: bool | None = Query(None),
    has_articles: bool | None = Query(None),
) -> dict:
    svc = PublicService(db, redis)
    return await svc.list_article_themes(active=active, has_articles=has_articles)


@router.get("/articles/{slug}", response_model=ArticleDetailResponse)
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> ArticleDetailResponse:
    svc = PublicService(db, redis)
    return await svc.get_article(slug)


# ── Organization documents ───────────────────────────────────────

@router.get("/organization-documents")
async def list_organization_documents(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    from sqlalchemy import select

    from app.models.content import OrganizationDocument

    result = await db.execute(
        select(OrganizationDocument)
        .where(OrganizationDocument.is_active.is_(True))
        .order_by(OrganizationDocument.sort_order)
    )
    docs = result.scalars().all()
    return {
        "data": [
            {
                "id": str(d.id),
                "title": d.title,
                "slug": d.slug,
                "content": d.content,
                "file_url": d.file_url,
            }
            for d in docs
        ]
    }


# ── SEO (for frontend SSR) ──────────────────────────────────────

@router.get("/seo/{slug}")
async def get_seo_page(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    from app.services.seo_service import SeoService

    svc = SeoService(db)
    return (await svc.get_by_slug(slug)).model_dump()
