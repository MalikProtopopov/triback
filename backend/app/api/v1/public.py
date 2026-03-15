"""Public (guest) endpoints — no authentication required."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_optional_user_id
from app.core.openapi import error_responses
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
    ArticleThemeListResponse,
    CityWithDoctorsResponse,
    ContentBlockPublicNested,
    DoctorPublicDetailResponse,
    DoctorPublicListItem,
    EventPublicDetailResponse,
    EventPublicListItem,
    GalleryListResponse,
    OrgDocPublicListResponse,
    OrgDocPublicDetailResponse,
    RecordingListResponse,
)
from app.schemas.seo import SeoPageResponse
from app.services.public_service import PublicService

router = APIRouter()


# ── Cities ────────────────────────────────────────────────────────

@router.get(
    "/cities",
    response_model=dict,
    summary="Список городов",
)
async def list_cities(
    with_doctors: bool = Query(False, description="Если true — только города с врачами, с подсчётом"),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> dict:
    """Возвращает список городов. С `with_doctors=true` дополнительно
    считает количество активных врачей в каждом городе."""
    svc = PublicService(db, redis)
    return await svc.list_cities(with_doctors=with_doctors)


@router.get(
    "/cities/{slug}",
    response_model=CityWithDoctorsResponse,
    summary="Город по slug",
    responses=error_responses(404),
)
async def get_city(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> CityWithDoctorsResponse:
    """Информация о городе по slug (включая количество врачей).

    - **404** — город не найден
    """
    svc = PublicService(db, redis)
    return await svc.get_city(slug)


# ── Doctors (public catalog) ─────────────────────────────────────

@router.get(
    "/doctors",
    response_model=PaginatedResponse[DoctorPublicListItem],
    summary="Каталог врачей",
)
async def list_doctors(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    limit: int = Query(12, ge=1, le=50),
    offset: int = Query(0, ge=0),
    city_id: UUID | None = Query(None, description="Фильтр по UUID города"),
    city_slug: str | None = Query(None, description="Фильтр по slug города"),
    specialization: str | None = Query(None),
    search: str | None = Query(None, min_length=2, description="Поиск по ФИО (мин. 2 символа)"),
) -> dict:
    """Пагинированный список активных врачей с фильтрацией."""
    svc = PublicService(db, redis)
    return await svc.list_doctors(
        limit=limit,
        offset=offset,
        city_id=city_id,
        city_slug=city_slug,
        specialization=specialization,
        search=search,
    )


@router.get(
    "/doctors/{identifier}",
    response_model=DoctorPublicDetailResponse,
    summary="Профиль врача",
    responses=error_responses(404),
)
async def get_doctor(
    identifier: str,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> DoctorPublicDetailResponse:
    """Детальная карточка врача по UUID или slug.

    - **404** — врач не найден или неактивен
    """
    svc = PublicService(db, redis)
    return await svc.get_doctor(identifier)


# ── Events ────────────────────────────────────────────────────────

@router.get(
    "/events",
    response_model=PaginatedResponse[EventPublicListItem],
    summary="Список мероприятий",
)
async def list_events(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    period: str = Query("upcoming", description="upcoming | past | all"),
) -> dict:
    """Пагинированный список мероприятий с фильтром по периоду."""
    svc = PublicService(db, redis)
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
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> EventPublicDetailResponse:
    """Полная информация о мероприятии по slug, включая тарифы, галереи и записи.

    - **404** — мероприятие не найдено
    """
    svc = PublicService(db, redis)
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


# ── Event Galleries (D18) ────────────────────────────────────────

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

@router.get(
    "/articles",
    response_model=PaginatedResponse[ArticleListItem],
    summary="Список статей",
)
async def list_articles(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    theme_slug: str | None = Query(None, description="Фильтр по slug темы"),
    search: str | None = Query(None, min_length=2, description="Полнотекстовый поиск"),
) -> dict:
    """Пагинированный список опубликованных статей."""
    svc = PublicService(db, redis)
    return await svc.list_articles(
        limit=limit, offset=offset, theme_slug=theme_slug, search=search
    )


@router.get(
    "/article-themes",
    response_model=ArticleThemeListResponse,
    summary="Список тем статей",
)
async def list_article_themes(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    active: bool | None = Query(None, description="Фильтр по активности"),
    has_articles: bool | None = Query(None, description="Только темы со статьями"),
) -> dict:
    """Список тем для фильтрации статей."""
    svc = PublicService(db, redis)
    return await svc.list_article_themes(active=active, has_articles=has_articles)


@router.get(
    "/articles/{slug}",
    response_model=ArticleDetailResponse,
    summary="Статья по slug",
    responses=error_responses(404),
)
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> ArticleDetailResponse:
    """Полный текст статьи с метаданными и SEO.

    - **404** — статья не найдена
    """
    svc = PublicService(db, redis)
    return await svc.get_article(slug)


# ── Organization documents ───────────────────────────────────────

@router.get(
    "/organization-documents",
    response_model=OrgDocPublicListResponse,
    summary="Документы организации",
)
async def list_organization_documents(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Список активных документов организации (устав, положения и т.д.)."""
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


@router.get(
    "/organization-documents/{slug}",
    response_model=OrgDocPublicDetailResponse,
    summary="Документ организации по slug",
    responses=error_responses(404),
)
async def get_organization_document(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> OrgDocPublicDetailResponse:
    """Детальная страница документа организации по slug.

    - **404** — документ не найден
    """
    from sqlalchemy import select

    from app.models.content import ContentBlock, OrganizationDocument

    result = await db.execute(
        select(OrganizationDocument).where(
            OrganizationDocument.slug == slug,
            OrganizationDocument.is_active.is_(True),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Document not found")

    blocks_result = await db.execute(
        select(ContentBlock)
        .where(
            ContentBlock.entity_type == "organization_document",
            ContentBlock.entity_id == doc.id,
        )
        .order_by(ContentBlock.sort_order.asc())
    )
    blocks = blocks_result.scalars().all()

    return OrgDocPublicDetailResponse(
        id=str(doc.id),
        title=doc.title,
        slug=doc.slug,
        content=doc.content,
        file_url=doc.file_url,
        content_blocks=[
            ContentBlockPublicNested(
                id=str(b.id),
                block_type=b.block_type,
                sort_order=b.sort_order,
                title=b.title,
                content=b.content,
                media_url=b.media_url,
                thumbnail_url=b.thumbnail_url,
                link_url=b.link_url,
                link_label=b.link_label,
                device_type=b.device_type,
            )
            for b in blocks
        ],
    )


# ── SEO (for frontend SSR) ──────────────────────────────────────

@router.get(
    "/seo/{slug}",
    response_model=SeoPageResponse,
    summary="SEO-метаданные страницы",
    responses=error_responses(404),
)
async def get_seo_page(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Возвращает SEO-метатеги для указанной страницы по slug.

    - **404** — SEO-страница не найдена
    """
    from app.services.seo_service import SeoService

    svc = SeoService(db)
    return (await svc.get_by_slug(slug)).model_dump()
