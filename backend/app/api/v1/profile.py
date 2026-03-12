"""Profile router — personal/public profile, photo/diploma uploads, my events."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user_id
from app.schemas.auth import MessageResponse
from app.schemas.event_registration import MyEventListItem
from app.schemas.profile import (
    DiplomaPhotoResponse,
    DocumentNested,
    PersonalProfileResponse,
    PersonalProfileUpdate,
    PhotoUploadResponse,
    PublicProfileResponse,
    PublicProfileUpdate,
)
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile")


@router.get("/personal", response_model=PersonalProfileResponse)
async def get_personal(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> PersonalProfileResponse:
    svc = ProfileService(db)
    profile = await svc.get_personal(user_id)

    city_data = None
    if profile.city:
        city_data = {"id": profile.city.id, "name": profile.city.name}

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
        diploma_photo_url=profile.diploma_photo_url,
        colleague_contacts=profile.colleague_contacts,
        documents=documents,
    )


@router.patch("/personal", response_model=MessageResponse)
async def update_personal(
    data: PersonalProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    svc = ProfileService(db)
    update_data = data.model_dump(exclude_unset=True)
    await svc.update_personal(user_id, update_data)
    return MessageResponse(message="Данные обновлены")


@router.post("/diploma-photo", response_model=DiplomaPhotoResponse, status_code=201)
async def upload_diploma_photo(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> DiplomaPhotoResponse:
    svc = ProfileService(db)
    s3_key = await svc.upload_diploma_photo(user_id, file)
    return DiplomaPhotoResponse(
        diploma_photo_url=s3_key,
        message="Фото диплома загружено",
    )


@router.get("/public", response_model=PublicProfileResponse)
async def get_public(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> PublicProfileResponse:
    svc = ProfileService(db)
    result = await svc.get_public(user_id)
    return PublicProfileResponse(**result)


@router.patch("/public", response_model=MessageResponse)
async def update_public(
    data: PublicProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    svc = ProfileService(db)
    update_data = data.model_dump(exclude_unset=True)
    await svc.update_public(user_id, update_data)
    return MessageResponse(message="Изменения отправлены на модерацию")


@router.post("/photo", response_model=PhotoUploadResponse, status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> PhotoUploadResponse:
    svc = ProfileService(db)
    s3_key = await svc.upload_photo(user_id, file)
    return PhotoUploadResponse(
        photo_url=s3_key,
        message="Фото профиля обновлено",
    )


# ── D17: My events ──────────────────────────────────────────────

@router.get("/events", response_model=dict)
async def list_my_events(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    from sqlalchemy import func, select

    from app.models.events import Event, EventRegistration

    base = (
        select(EventRegistration, Event)
        .join(Event, EventRegistration.event_id == Event.id)
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
            title=evt.title,
            event_date=evt.event_date,
            status=reg.status,
            applied_price=float(reg.applied_price),
            is_member_price=reg.is_member_price,
        )
        for reg, evt in rows
    ]
    return {"data": items, "total": total, "limit": limit, "offset": offset}
