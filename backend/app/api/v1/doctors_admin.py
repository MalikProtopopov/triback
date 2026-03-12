"""Admin endpoints for doctor management and moderation."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.pagination import PaginatedResponse
from app.core.redis import get_redis
from app.core.security import require_role
from app.schemas.auth import MessageResponse
from app.schemas.doctor_admin import (
    ApproveDraftRequest,
    DoctorDetailResponse,
    DoctorListItemResponse,
    ImportStartResponse,
    ImportStatusResponse,
    ModerateRequest,
    ModerateResponse,
    PortalUserDetailResponse,
    PortalUserListItem,
    SendEmailRequest,
    SendReminderRequest,
    ToggleActiveRequest,
    ToggleActiveResponse,
)
from app.services.doctor_service import DoctorAdminService

router = APIRouter(prefix="/admin")

ADMIN_MANAGER = require_role("admin", "manager")
ADMIN_ONLY = require_role("admin")


# ── GET /admin/doctors ────────────────────────────────────────────

@router.get("/doctors", response_model=PaginatedResponse[DoctorListItemResponse])
async def list_doctors(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    subscription_status: str | None = Query(None),
    city_id: UUID | None = Query(None),
    has_data_changed: bool | None = Query(None),
    search: str | None = Query(None, min_length=2),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> dict[str, Any]:
    svc = DoctorAdminService(db)
    return await svc.list_doctors(
        limit=limit,
        offset=offset,
        status=status,
        subscription_status=subscription_status,
        city_id=city_id,
        has_data_changed=has_data_changed,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# ── GET /admin/doctors/{id} ──────────────────────────────────────

@router.get("/doctors/{profile_id}", response_model=DoctorDetailResponse)
async def get_doctor(
    profile_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> DoctorDetailResponse:
    svc = DoctorAdminService(db)
    return await svc.get_doctor(profile_id)


# ── POST /admin/doctors/{id}/moderate ─────────────────────────────

@router.post("/doctors/{profile_id}/moderate", response_model=ModerateResponse)
async def moderate_doctor(
    profile_id: UUID,
    body: ModerateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ModerateResponse:
    admin_id = UUID(payload["sub"])
    svc = DoctorAdminService(db)
    new_status = await svc.moderate(profile_id, admin_id, body.action, body.comment)
    msg = "Врач одобрен" if body.action == "approve" else "Врач отклонён"
    return ModerateResponse(moderation_status=new_status, message=msg)


# ── POST /admin/doctors/{id}/approve-draft ────────────────────────

@router.post("/doctors/{profile_id}/approve-draft", response_model=MessageResponse)
async def approve_draft(
    profile_id: UUID,
    body: ApproveDraftRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    admin_id = UUID(payload["sub"])
    svc = DoctorAdminService(db)
    msg = await svc.approve_draft(
        profile_id, admin_id, body.action, body.rejection_reason
    )
    return MessageResponse(message=msg)


# ── POST /admin/doctors/{id}/toggle-active ────────────────────────

@router.post("/doctors/{profile_id}/toggle-active", response_model=ToggleActiveResponse)
async def toggle_active(
    profile_id: UUID,
    body: ToggleActiveRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ToggleActiveResponse:
    admin_id = UUID(payload["sub"])
    svc = DoctorAdminService(db)
    is_public = await svc.toggle_active(profile_id, admin_id, body.is_public)
    msg = "Профиль активирован" if is_public else "Профиль деактивирован"
    return ToggleActiveResponse(is_public=is_public, message=msg)


# ── POST /admin/doctors/{id}/send-reminder ────────────────────────

@router.post("/doctors/{profile_id}/send-reminder", response_model=MessageResponse)
async def send_reminder(
    profile_id: UUID,
    body: SendReminderRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    svc = DoctorAdminService(db)
    await svc.send_reminder(profile_id, body.message)
    return MessageResponse(message="Напоминание отправлено")


# ── POST /admin/doctors/{id}/send-email ───────────────────────────

@router.post("/doctors/{profile_id}/send-email", response_model=MessageResponse)
async def send_email(
    profile_id: UUID,
    body: SendEmailRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    svc = DoctorAdminService(db)
    await svc.send_email(profile_id, body.subject, body.body)
    return MessageResponse(message="Письмо отправлено")


# ── POST /admin/doctors/import ────────────────────────────────────

@router.post("/doctors/import", response_model=ImportStartResponse, status_code=202)
async def import_doctors(
    file: UploadFile,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> ImportStartResponse:
    contents = await file.read()
    svc = DoctorAdminService(db)
    task_id = await svc.start_import(contents, redis)
    return ImportStartResponse(task_id=task_id, message="Импорт запущен")


# ── GET /admin/doctors/import/{task_id} ───────────────────────────

@router.get("/doctors/import/{task_id}", response_model=ImportStatusResponse)
async def get_import_status(
    task_id: str,
    payload: dict[str, Any] = ADMIN_ONLY,
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> ImportStatusResponse:
    svc = DoctorAdminService(db=None)  # type: ignore[arg-type]
    return await svc.get_import_status(task_id, redis)


# ── GET /admin/portal-users/{user_id} ────────────────────────────

@router.get("/portal-users/{user_id}", response_model=PortalUserDetailResponse)
async def get_portal_user(
    user_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> PortalUserDetailResponse:
    svc = DoctorAdminService(db)
    return await svc.get_portal_user(user_id)


# ── GET /admin/portal-users ──────────────────────────────────────

@router.get("/portal-users", response_model=PaginatedResponse[PortalUserListItem])
async def list_portal_users(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, min_length=2),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> dict[str, Any]:
    svc = DoctorAdminService(db)
    return await svc.list_portal_users(
        limit=limit,
        offset=offset,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
