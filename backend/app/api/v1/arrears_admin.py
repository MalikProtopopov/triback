"""Admin API — membership arrears."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.schemas.arrears import (
    ArrearCreateRequest,
    ArrearListResponse,
    ArrearResponse,
    ArrearSummaryResponse,
    ArrearUpdateRequest,
    ArrearWaiveRequest,
)
from app.services.arrears_admin_service import ArrearsAdminService

router = APIRouter(prefix="/admin")

ADMIN_ACCOUNTANT = require_role("admin", "accountant")


@router.get(
    "/arrears",
    response_model=ArrearListResponse,
    summary="Список задолженностей",
    responses=error_responses(401, 403),
)
async def list_arrears(
    payload: dict[str, Any] = ADMIN_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: UUID | None = None,
    year: int | None = None,
    status: str | None = Query(None, description="open | paid | cancelled | waived"),
    source: str | None = Query(None, description="manual | automatic"),
    include_inactive: bool = Query(
        True,
        description="Если false — только открытые (open); полная история при true без фильтра status",
    ),
) -> ArrearListResponse:
    svc = ArrearsAdminService(db)
    return await svc.list_arrears(
        limit=limit,
        offset=offset,
        user_id=user_id,
        year=year,
        status=status,
        source=source,
        include_inactive=include_inactive,
    )


@router.get(
    "/arrears/summary",
    response_model=ArrearSummaryResponse,
    summary="Сводка по задолженностям",
    responses=error_responses(401, 403),
)
async def arrears_summary(
    payload: dict[str, Any] = ADMIN_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
) -> ArrearSummaryResponse:
    svc = ArrearsAdminService(db)
    return await svc.summary()


@router.post(
    "/arrears",
    response_model=ArrearResponse,
    status_code=201,
    summary="Создать задолженность",
    responses=error_responses(401, 403, 404, 409, 422),
)
async def create_arrear(
    body: ArrearCreateRequest,
    payload: dict[str, Any] = ADMIN_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
) -> ArrearResponse:
    admin_id = UUID(payload["sub"])
    svc = ArrearsAdminService(db)
    return await svc.create(admin_id, body)


@router.patch(
    "/arrears/{arrear_id}",
    response_model=ArrearResponse,
    summary="Изменить задолженность",
    responses=error_responses(401, 403, 404, 422),
)
async def update_arrear(
    arrear_id: UUID,
    body: ArrearUpdateRequest,
    payload: dict[str, Any] = ADMIN_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
) -> ArrearResponse:
    svc = ArrearsAdminService(db)
    return await svc.update(arrear_id, body)


@router.post(
    "/arrears/{arrear_id}/cancel",
    response_model=ArrearResponse,
    summary="Отменить задолженность",
    responses=error_responses(401, 403, 404, 422),
)
async def cancel_arrear(
    arrear_id: UUID,
    payload: dict[str, Any] = ADMIN_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
) -> ArrearResponse:
    svc = ArrearsAdminService(db)
    return await svc.cancel(arrear_id)


@router.post(
    "/arrears/{arrear_id}/waive",
    response_model=ArrearResponse,
    summary="Простить задолженность",
    responses=error_responses(401, 403, 404, 422),
)
async def waive_arrear(
    arrear_id: UUID,
    body: ArrearWaiveRequest,
    payload: dict[str, Any] = ADMIN_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
) -> ArrearResponse:
    admin_id = UUID(payload["sub"])
    svc = ArrearsAdminService(db)
    return await svc.waive(arrear_id, admin_id, body.waive_reason)


@router.post(
    "/arrears/{arrear_id}/mark-paid",
    response_model=ArrearResponse,
    summary="Отметить оплаченной вручную без провайдера",
    responses=error_responses(401, 403, 404, 422),
)
async def mark_arrear_paid(
    arrear_id: UUID,
    payload: dict[str, Any] = ADMIN_ACCOUNTANT,
    db: AsyncSession = Depends(get_db_session),
) -> ArrearResponse:
    svc = ArrearsAdminService(db)
    return await svc.mark_paid_manual(arrear_id)
