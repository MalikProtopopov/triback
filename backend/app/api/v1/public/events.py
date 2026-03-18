"""Public event endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_optional_user_id
from app.core.enums import EventRegistrationStatus, SubscriptionStatus
from app.core.exceptions import NotFoundError
from app.core.openapi import error_responses
from app.core.pagination import PaginatedResponse
from app.core.redis import get_redis
from app.models.events import (
    Event,
    EventGallery,
    EventGalleryPhoto,
    EventRecording,
    EventRegistration,
)
from app.models.subscriptions import Subscription
from app.schemas.event_registration import (
    ConfirmGuestRegistrationRequest,
    RegisterForEventRequest,
    RegisterForEventResponse,
)
from app.schemas.public import (
    EventPublicDetailResponse,
    EventPublicListItem,
    GalleryListResponse,
    RecordingListResponse,
)
from app.services import file_service
from app.services.event_public_service import EventPublicService

router = APIRouter()


@router.get(
    "/events",
    response_model=PaginatedResponse[EventPublicListItem],
    summary="Список мероприятий",
)
async def list_events(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    period: str = Query("upcoming", description="upcoming | past | all"),
) -> dict:
    """Пагинированный список мероприятий с фильтром по периоду."""
    svc = EventPublicService(db)
    return await svc.list_events(limit=limit, offset=offset, period=period)


@router.get(
    "/events/{slug}",
    response_model=EventPublicDetailResponse,
    summary="Детали мероприятия",
    responses=error_responses(404),
)
async def get_event(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> EventPublicDetailResponse:
    """Полная информация о мероприятии по slug, включая тарифы, галереи и записи.

    - **404** — мероприятие не найдено
    """
    svc = EventPublicService(db)
    return await svc.get_event(slug)


@router.post(
    "/events/{event_id}/register",
    response_model=RegisterForEventResponse,
    status_code=201,
    summary="Регистрация на мероприятие",
    responses=error_responses(404, 409, 422, 429),
)
async def register_for_event(
    event_id: UUID,
    body: RegisterForEventRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    user_id: UUID | None = Depends(get_optional_user_id),
) -> RegisterForEventResponse:
    """Регистрирует пользователя на мероприятие. Три сценария:

    1. **Авторизованный пользователь** → создаёт регистрацию и платёж, возвращает `payment_url`
    2. **Гость с существующим аккаунтом** → `action="login_required"`, `masked_email="m***@mail.ru"`
    3. **Новый гость** → `action="verification_required"`, отправляет код на email

    - **404** — мероприятие или тариф не найдены
    - **409** — уже зарегистрирован, нет мест, мероприятие закрыто
    - **429** — слишком много отправок кода (макс. 3 за 10 мин)
    """
    from app.services.event_registration_service import EventRegistrationService

    svc = EventRegistrationService(db, redis)
    return await svc.register(event_id, user_id, body)


@router.post(
    "/events/{event_id}/confirm-guest-registration",
    response_model=RegisterForEventResponse,
    status_code=201,
    summary="Подтверждение гостевой регистрации",
    responses=error_responses(404, 409, 422, 429),
)
async def confirm_guest_registration(
    event_id: UUID,
    body: ConfirmGuestRegistrationRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> RegisterForEventResponse:
    """Подтверждает email гостя 6-значным кодом и создаёт регистрацию + платёж.
    Возвращает `payment_url` для оплаты.

    - **404** — мероприятие/тариф не найден, код не найден/истёк
    - **409** — неверный код (макс. 5 попыток), нет мест
    - **429** — превышен лимит попыток ввода кода
    """
    from app.services.event_registration_service import EventRegistrationService

    svc = EventRegistrationService(db, redis)
    return await svc.confirm_guest_registration(event_id, body)


# ── Event Galleries ──────────────────────────────────────────────

@router.get(
    "/events/{event_id}/galleries",
    response_model=GalleryListResponse,
    summary="Галереи мероприятия",
    responses=error_responses(404),
)
async def list_event_galleries(
    event_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID | None = Depends(get_optional_user_id),
) -> dict:
    """Список галерей с фотографиями. Галереи с `access_level=members_only`
    видны только участникам (с подпиской или подтверждённой регистрацией).

    - **404** — мероприятие не найдено
    """
    event = await db.get(Event, event_id)
    if not event:
        raise NotFoundError("Event not found")

    has_access = False
    if user_id:
        sub = (await db.execute(
            select(Subscription.id).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                or_(
                    Subscription.ends_at.is_(None),
                    Subscription.ends_at > func.now(),
                ),
            ).limit(1)
        )).scalar_one_or_none()
        reg = (await db.execute(
            select(EventRegistration.id).where(
                EventRegistration.user_id == user_id,
                EventRegistration.event_id == event_id,
                EventRegistration.status == EventRegistrationStatus.CONFIRMED,
            ).limit(1)
        )).scalar_one_or_none()
        has_access = sub is not None or reg is not None

    galleries_q = (
        select(EventGallery)
        .where(EventGallery.event_id == event_id)
        .order_by(EventGallery.sort_order)
    )
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
                {
                    "id": str(p.id),
                    "file_url": file_service.build_media_url(p.file_url),
                    "thumbnail_url": file_service.build_media_url(p.thumbnail_url),
                    "caption": p.caption,
                }
                for p in photos
            ],
        })
    return {"data": items}


# ── Event Recordings ─────────────────────────────────────────────

@router.get(
    "/events/{event_id}/recordings",
    response_model=RecordingListResponse,
    summary="Записи мероприятия",
    responses=error_responses(404),
)
async def list_event_recordings(
    event_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID | None = Depends(get_optional_user_id),
) -> dict:
    """Список видеозаписей мероприятия. Записи с `access_level` members_only/participants_only
    видны только при наличии активной подписки или подтверждённой регистрации.

    - **404** — мероприятие не найдено
    """
    event = await db.get(Event, event_id)
    if not event:
        raise NotFoundError("Event not found")

    has_access = False
    if user_id:
        sub = (await db.execute(
            select(Subscription.id).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                or_(
                    Subscription.ends_at.is_(None),
                    Subscription.ends_at > func.now(),
                ),
            ).limit(1)
        )).scalar_one_or_none()
        reg = (await db.execute(
            select(EventRegistration.id).where(
                EventRegistration.user_id == user_id,
                EventRegistration.event_id == event_id,
                EventRegistration.status == EventRegistrationStatus.CONFIRMED,
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
