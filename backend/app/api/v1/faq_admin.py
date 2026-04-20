"""Admin FAQ CRUD endpoints — requires admin or manager role."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.pagination import PaginatedResponse
from app.core.security import require_role
from app.schemas.faq import FaqAdminItem, FaqCreateRequest, FaqUpdateRequest
from app.services.faq_service import FaqAdminService

router = APIRouter(prefix="/admin/faq")

ADMIN_MANAGER = require_role("admin", "manager")
ADMIN_ONLY = require_role("admin")


@router.get(
    "",
    response_model=PaginatedResponse[FaqAdminItem],
    summary="Список всех FAQ",
    responses=error_responses(401, 403),
)
async def list_faq(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_active: bool | None = Query(None, description="Фильтр по активности"),
    search: str | None = Query(None, min_length=2, description="Поиск по тексту"),
) -> dict[str, Any]:
    """Пагинированный список всех FAQ-записей (включая неактивные)."""
    svc = FaqAdminService(db)
    return await svc.list_all(
        limit=limit, offset=offset, is_active=is_active, search=search,
    )


@router.post(
    "",
    response_model=FaqAdminItem,
    status_code=201,
    summary="Создать FAQ",
    responses=error_responses(401, 403, 422),
)
async def create_faq(
    body: FaqCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> FaqAdminItem:
    """Создаёт новую FAQ-запись."""
    svc = FaqAdminService(db)
    return await svc.create(body)


@router.get(
    "/{faq_id}",
    response_model=FaqAdminItem,
    summary="Детали FAQ",
    responses=error_responses(401, 403, 404),
)
async def get_faq(
    faq_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> FaqAdminItem:
    """Возвращает одну FAQ-запись по ID."""
    svc = FaqAdminService(db)
    return await svc.get_by_id(faq_id)


@router.patch(
    "/{faq_id}",
    response_model=FaqAdminItem,
    summary="Обновить FAQ",
    responses=error_responses(401, 403, 404, 422),
)
async def update_faq(
    faq_id: UUID,
    body: FaqUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> FaqAdminItem:
    """Обновляет поля FAQ-записи. Все поля optional — передаются только изменённые."""
    svc = FaqAdminService(db)
    return await svc.update(faq_id, body)


@router.delete(
    "/{faq_id}",
    status_code=204,
    summary="Удалить FAQ",
    responses=error_responses(401, 403, 404),
)
async def delete_faq(
    faq_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Удаляет FAQ-запись. Только admin."""
    svc = FaqAdminService(db)
    await svc.delete(faq_id)
    return Response(status_code=204)
