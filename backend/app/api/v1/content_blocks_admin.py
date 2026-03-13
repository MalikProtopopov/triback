"""Admin endpoints for content blocks CRUD and reordering."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.schemas.content_blocks import (
    ContentBlockCreateRequest,
    ContentBlockListResponse,
    ContentBlockReorderRequest,
    ContentBlockResponse,
    ContentBlockUpdateRequest,
)
from app.services.content_block_service import ContentBlockService

router = APIRouter(prefix="/admin")

ADMIN_MANAGER = require_role("admin", "manager")


@router.get(
    "/content-blocks",
    response_model=ContentBlockListResponse,
    summary="Список контентных блоков",
    responses=error_responses(401, 403, 422),
)
async def list_content_blocks(
    entity_type: str = Query(..., description="article | event | doctor_profile | organization_document"),
    entity_id: UUID = Query(..., description="UUID сущности-владельца"),
    locale: str = Query("ru", max_length=5),
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ContentBlockListResponse:
    """Список контентных блоков для конкретной сущности, отсортированных по sort_order.

    - **401** -- не авторизован
    - **403** -- роль не admin/manager
    """
    svc = ContentBlockService(db)
    return await svc.list_blocks(entity_type, entity_id, locale)


@router.post(
    "/content-blocks",
    response_model=ContentBlockResponse,
    status_code=201,
    summary="Создать контентный блок",
    responses=error_responses(401, 403, 422),
)
async def create_content_block(
    body: ContentBlockCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ContentBlockResponse:
    """Создаёт новый контентный блок для сущности.

    - **401** -- не авторизован
    - **403** -- роль не admin/manager
    """
    svc = ContentBlockService(db)
    return await svc.create_block(body.model_dump())


@router.patch(
    "/content-blocks/{block_id}",
    response_model=ContentBlockResponse,
    summary="Обновить контентный блок",
    responses=error_responses(401, 403, 404, 422),
)
async def update_content_block(
    block_id: UUID,
    body: ContentBlockUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ContentBlockResponse:
    """Обновляет поля контентного блока. Можно отправлять только изменённые поля.

    - **404** -- блок не найден
    """
    svc = ContentBlockService(db)
    return await svc.update_block(block_id, body.model_dump(exclude_unset=True))


@router.delete(
    "/content-blocks/{block_id}",
    status_code=204,
    summary="Удалить контентный блок",
    responses=error_responses(401, 403, 404),
)
async def delete_content_block(
    block_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Удаляет контентный блок.

    - **404** -- блок не найден
    """
    svc = ContentBlockService(db)
    await svc.delete_block(block_id)
    return Response(status_code=204)


@router.post(
    "/content-blocks/reorder",
    response_model=list[ContentBlockResponse],
    summary="Перестановка блоков",
    responses=error_responses(401, 403, 404, 422),
)
async def reorder_content_blocks(
    body: ContentBlockReorderRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> list[ContentBlockResponse]:
    """Массовое обновление sort_order для контентных блоков.

    - **404** -- один из блоков не найден
    """
    svc = ContentBlockService(db)
    return await svc.reorder_blocks([item.model_dump() for item in body.items])
