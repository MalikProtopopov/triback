"""Profile router — personal/public profile, photo/diploma uploads, my events."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user_id
from app.core.openapi import error_responses
from app.schemas.auth import MessageResponse
from app.schemas.event_registration import MyEventListItem, MyEventsPaginatedResponse
from app.schemas.profile import (
    DiplomaPhotoResponse,
    DocumentNested,
    PersonalProfileResponse,
    PersonalProfileUpdate,
    PhotoUploadResponse,
    PublicProfileResponse,
    PublicProfileUpdate,
)
from app.schemas.shared import CityNested
from app.services import file_service
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile")


@router.get(
    "/personal",
    response_model=PersonalProfileResponse,
    summary="Личные данные",
    responses=error_responses(401, 404),
)
async def get_personal(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> PersonalProfileResponse:
    """Возвращает личные (непубличные) данные профиля врача.

    - **401** — не авторизован
    - **404** — профиль ещё не создан
    """
    svc = ProfileService(db)
    profile = await svc.get_personal(user_id)

    city_data: CityNested | None = None
    if profile.city:
        city_data = CityNested(id=profile.city.id, name=profile.city.name)

    documents = [
        DocumentNested(
            id=d.id,
            document_type=d.document_type,
            original_filename=d.original_filename,
            uploaded_at=d.uploaded_at,
        )
        for d in profile.documents
    ]

    return PersonalProfileResponse(
        first_name=profile.first_name,
        last_name=profile.last_name,
        middle_name=profile.middle_name,
        phone=profile.phone,
        passport_data=profile.passport_data,
        registration_address=profile.registration_address,
        city=city_data,
        clinic_name=profile.clinic_name,
        position=profile.position,
        academic_degree=profile.academic_degree,
        specialization=profile.specialization,
        diploma_photo_url=file_service.build_media_url(profile.diploma_photo_url),
        colleague_contacts=profile.colleague_contacts,
        documents=documents,
    )


@router.patch(
    "/personal",
    response_model=MessageResponse,
    summary="Обновить личные данные",
    responses=error_responses(401, 404, 422),
)
async def update_personal(
    data: PersonalProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Обновляет личные данные профиля. Можно отправлять только изменённые поля.

    - **401** — не авторизован
    - **404** — профиль не найден
    """
    svc = ProfileService(db)
    update_data = data.model_dump(exclude_unset=True)
    await svc.update_personal(user_id, update_data)
    return MessageResponse(message="Данные обновлены")


@router.post(
    "/diploma-photo",
    response_model=DiplomaPhotoResponse,
    status_code=201,
    summary="Загрузка фото диплома",
    responses=error_responses(401, 422),
)
async def upload_diploma_photo(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> DiplomaPhotoResponse:
    """Загружает фото диплома в S3 и сохраняет URL в профиле.

    - **401** — не авторизован
    """
    svc = ProfileService(db)
    s3_key = await svc.upload_diploma_photo(user_id, file)
    return DiplomaPhotoResponse(
        diploma_photo_url=file_service.build_media_url(s3_key) or "",
        message="Фото диплома загружено",
    )


@router.get(
    "/public",
    response_model=PublicProfileResponse,
    summary="Публичный профиль",
    responses=error_responses(401, 404),
)
async def get_public(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> PublicProfileResponse:
    """Данные публичного профиля врача (видимые в каталоге).

    - **401** — не авторизован
    - **404** — профиль не найден
    """
    svc = ProfileService(db)
    result = await svc.get_public(user_id)
    return PublicProfileResponse(**result)


@router.patch(
    "/public",
    response_model=MessageResponse,
    summary="Обновить публичный профиль",
    responses=error_responses(401, 404, 422),
)
async def update_public(
    data: PublicProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Обновляет публичные данные. Изменения отправляются на модерацию.

    - **401** — не авторизован
    - **404** — профиль не найден
    """
    svc = ProfileService(db)
    update_data = data.model_dump(exclude_unset=True, mode="json")
    await svc.update_public(user_id, update_data)
    return MessageResponse(message="Изменения отправлены на модерацию")


@router.post(
    "/photo",
    response_model=PhotoUploadResponse,
    status_code=201,
    summary="Загрузка фото профиля",
    responses=error_responses(401, 422),
)
async def upload_photo(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> PhotoUploadResponse:
    """Загружает фото профиля врача в S3.

    - **401** — не авторизован
    """
    svc = ProfileService(db)
    result = await svc.upload_photo(user_id, file)
    return PhotoUploadResponse(
        photo_url=result["photo_url"],
        message="Фото загружено и отправлено на модерацию",
        pending_moderation=result["pending_moderation"],
    )


# ── D17: My events ──────────────────────────────────────────────

@router.get(
    "/events",
    response_model=MyEventsPaginatedResponse,
    summary="Мои мероприятия",
    responses=error_responses(401),
)
async def list_my_events(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Список мероприятий, на которые пользователь зарегистрирован (confirmed).

    - **401** — не авторизован
    """
    from sqlalchemy import func, select

    from app.models.events import Event, EventRegistration, EventTariff

    base = (
        select(EventRegistration, Event, EventTariff)
        .join(Event, EventRegistration.event_id == Event.id)
        .outerjoin(EventTariff, EventRegistration.event_tariff_id == EventTariff.id)
        .where(
            EventRegistration.user_id == user_id,
            EventRegistration.status == "confirmed",
        )
        .order_by(Event.event_date.desc())
    )
    count_q = (
        select(func.count(EventRegistration.id))
        .where(
            EventRegistration.user_id == user_id,
            EventRegistration.status == "confirmed",
        )
    )
    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(base.offset(offset).limit(limit))).all()

    items = [
        MyEventListItem(
            registration_id=reg.id,
            event_id=evt.id,
            event_slug=evt.slug,
            title=evt.title,
            event_date=evt.event_date,
            status=reg.status,
            applied_price=float(reg.applied_price),
            is_member_price=reg.is_member_price,
            tariff_name=tariff.name if tariff else None,
        )
        for reg, evt, tariff in rows
    ]
    return {"data": items, "total": total, "limit": limit, "offset": offset}
