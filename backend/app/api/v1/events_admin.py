"""Admin endpoints for event management (events, tariffs, galleries, recordings)."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.pagination import PaginatedResponse
from app.core.security import require_role
from app.schemas.events_admin import (
    EventCreatedResponse,
    EventDetailResponse,
    EventListItem,
    GalleryCreateRequest,
    GalleryResponse,
    PhotoUploadResponse,
    RecordingCreateRequest,
    RecordingResponse,
    RecordingUpdateRequest,
    RegistrationListResponse,
    TariffCreateRequest,
    TariffResponse,
    TariffUpdateRequest,
)
from app.services.events_service import EventsAdminService

router = APIRouter(prefix="/admin/events")

ADMIN_MANAGER = require_role("admin", "manager")
ADMIN_ONLY = require_role("admin")


# ── Events CRUD ───────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[EventListItem])
async def list_events(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Literal["upcoming", "ongoing", "finished", "cancelled"] | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    sort_by: str = Query("event_date"),
    sort_order: str = Query("desc"),
) -> dict[str, Any]:
    svc = EventsAdminService(db)
    return await svc.list_events(
        limit=limit, offset=offset, status=status,
        date_from=date_from, date_to=date_to,
        sort_by=sort_by, sort_order=sort_order,
    )


@router.post("", response_model=EventCreatedResponse, status_code=201)
async def create_event(
    title: str = Form(..., max_length=500),
    event_date: datetime = Form(...),
    description: str | None = Form(None),
    event_end_date: datetime | None = Form(None),
    location: str | None = Form(None),
    status: Literal["upcoming", "ongoing", "finished", "cancelled"] = Form("upcoming"),
    cover_image: UploadFile | None = File(None),
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> EventCreatedResponse:
    admin_id = UUID(payload["sub"])
    svc = EventsAdminService(db)
    return await svc.create_event(
        admin_id,
        title=title, description=description, event_date=event_date,
        event_end_date=event_end_date, location=location, status=status,
        cover_image=cover_image,
    )


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> EventDetailResponse:
    svc = EventsAdminService(db)
    return await svc.get_event(event_id)


@router.patch("/{event_id}", response_model=EventDetailResponse)
async def update_event(
    event_id: UUID,
    title: str | None = Form(None),
    description: str | None = Form(None),
    event_date: datetime | None = Form(None),
    event_end_date: datetime | None = Form(None),
    location: str | None = Form(None),
    status: Literal["upcoming", "ongoing", "finished", "cancelled"] | None = Form(None),
    cover_image: UploadFile | None = File(None),
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> EventDetailResponse:
    data: dict[str, Any] = {}
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if event_date is not None:
        data["event_date"] = event_date
    if event_end_date is not None:
        data["event_end_date"] = event_end_date
    if location is not None:
        data["location"] = location
    if status is not None:
        data["status"] = status

    svc = EventsAdminService(db)
    return await svc.update_event(event_id, data=data, cover_image=cover_image)


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = EventsAdminService(db)
    await svc.delete_event(event_id)
    return Response(status_code=204)


# ── Tariffs ───────────────────────────────────────────────────────

@router.post("/{event_id}/tariffs", response_model=TariffResponse, status_code=201)
async def create_tariff(
    event_id: UUID,
    body: TariffCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> TariffResponse:
    svc = EventsAdminService(db)
    return await svc.create_tariff(event_id, body.model_dump())


@router.patch("/{event_id}/tariffs/{tariff_id}", response_model=TariffResponse)
async def update_tariff(
    event_id: UUID,
    tariff_id: UUID,
    body: TariffUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> TariffResponse:
    svc = EventsAdminService(db)
    return await svc.update_tariff(event_id, tariff_id, body.model_dump(exclude_none=True))


@router.delete("/{event_id}/tariffs/{tariff_id}", status_code=204)
async def delete_tariff(
    event_id: UUID,
    tariff_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = EventsAdminService(db)
    await svc.delete_tariff(event_id, tariff_id)
    return Response(status_code=204)


# ── Registrations ─────────────────────────────────────────────────

@router.get("/{event_id}/registrations", response_model=RegistrationListResponse)
async def list_registrations(
    event_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
) -> RegistrationListResponse:
    svc = EventsAdminService(db)
    return await svc.list_registrations(
        event_id, limit=limit, offset=offset, status=status,
    )


# ── Galleries + Photos ───────────────────────────────────────────

@router.post("/{event_id}/galleries", response_model=GalleryResponse, status_code=201)
async def create_gallery(
    event_id: UUID,
    body: GalleryCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> GalleryResponse:
    svc = EventsAdminService(db)
    return await svc.create_gallery(event_id, body.model_dump())


@router.post(
    "/{event_id}/galleries/{gallery_id}/photos",
    response_model=PhotoUploadResponse,
    status_code=201,
)
async def upload_gallery_photos(
    event_id: UUID,
    gallery_id: UUID,
    photos: list[UploadFile] = File(...),
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> PhotoUploadResponse:
    svc = EventsAdminService(db)
    return await svc.upload_photos(event_id, gallery_id, photos)


# ── Recordings ────────────────────────────────────────────────────

@router.post("/{event_id}/recordings", response_model=RecordingResponse, status_code=201)
async def create_recording(
    event_id: UUID,
    title: str = Form(...),
    video_source: str = Form(...),
    video_url: str | None = Form(None),
    duration_seconds: int | None = Form(None),
    access_level: str = Form(...),
    recording_status: str = Form("hidden"),
    video_file: UploadFile | None = File(None),
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> RecordingResponse:
    data = RecordingCreateRequest(
        title=title,
        video_source=video_source,  # type: ignore[arg-type]
        video_url=video_url,
        duration_seconds=duration_seconds,
        access_level=access_level,  # type: ignore[arg-type]
        status=recording_status,  # type: ignore[arg-type]
    )
    svc = EventsAdminService(db)
    return await svc.create_recording(event_id, data, video_file)


@router.patch("/{event_id}/recordings/{recording_id}", response_model=RecordingResponse)
async def update_recording(
    event_id: UUID,
    recording_id: UUID,
    body: RecordingUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> RecordingResponse:
    svc = EventsAdminService(db)
    return await svc.update_recording(event_id, recording_id, body)
