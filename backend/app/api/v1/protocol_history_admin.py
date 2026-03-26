"""Admin API — protocol history (admission / exclusion)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.schemas.protocol_history import (
    ProtocolHistoryCreateRequest,
    ProtocolHistoryListResponse,
    ProtocolHistoryResponse,
    ProtocolHistoryUpdateRequest,
)
from app.services.protocol_history_admin_service import ProtocolHistoryAdminService

router = APIRouter(prefix="/admin")

ADMIN_MANAGER = require_role("admin", "manager")


@router.get(
    "/protocol-history",
    response_model=ProtocolHistoryListResponse,
    summary="Список записей истории протокола",
    responses=error_responses(401, 403),
)
async def list_protocol_history(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    doctor_user_id: UUID | None = None,
    action_type: str | None = Query(
        None, description="admission | exclusion"
    ),
) -> ProtocolHistoryListResponse:
    svc = ProtocolHistoryAdminService(db)
    return await svc.list_entries(
        limit=limit,
        offset=offset,
        doctor_user_id=doctor_user_id,
        action_type=action_type,
    )


@router.get(
    "/protocol-history/{entry_id}",
    response_model=ProtocolHistoryResponse,
    summary="Запись истории протокола по id",
    responses=error_responses(401, 403, 404),
)
async def get_protocol_history(
    entry_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ProtocolHistoryResponse:
    svc = ProtocolHistoryAdminService(db)
    return await svc.get_by_id(entry_id)


@router.post(
    "/protocol-history",
    response_model=ProtocolHistoryResponse,
    status_code=201,
    summary="Создать запись истории протокола",
    responses=error_responses(401, 403, 404, 422),
)
async def create_protocol_history(
    body: ProtocolHistoryCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ProtocolHistoryResponse:
    actor_id = UUID(payload["sub"])
    svc = ProtocolHistoryAdminService(db)
    return await svc.create(actor_id, body)


@router.patch(
    "/protocol-history/{entry_id}",
    response_model=ProtocolHistoryResponse,
    summary="Изменить запись истории протокола",
    responses=error_responses(401, 403, 404, 422),
)
async def update_protocol_history(
    entry_id: UUID,
    body: ProtocolHistoryUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ProtocolHistoryResponse:
    actor_id = UUID(payload["sub"])
    svc = ProtocolHistoryAdminService(db)
    return await svc.update(entry_id, actor_id, body)


@router.delete(
    "/protocol-history/{entry_id}",
    status_code=204,
    summary="Удалить запись истории протокола",
    responses=error_responses(401, 403, 404),
)
async def delete_protocol_history(
    entry_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    svc = ProtocolHistoryAdminService(db)
    await svc.delete(entry_id)
