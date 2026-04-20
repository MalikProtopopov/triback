"""Public FAQ endpoints — no authentication required."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.pagination import PaginatedResponse
from app.schemas.faq import FaqPublicItem
from app.services.faq_service import FaqPublicService

router = APIRouter()


@router.get(
    "/faq",
    response_model=PaginatedResponse[FaqPublicItem],
    summary="Список вопросов и ответов",
)
async def list_faq(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, min_length=2, description="Поиск по тексту вопроса"),
    answered_only: bool = Query(False, description="Только с ответами"),
) -> dict[str, Any]:
    """Пагинированный список активных FAQ-записей.

    По умолчанию возвращает все активные вопросы, отсортированные по дате (новые первые).
    Фильтр `answered_only=true` вернёт только записи с непустым ответом.
    """
    svc = FaqPublicService(db)
    return await svc.list_active(
        limit=limit, offset=offset, search=search, answered_only=answered_only,
    )


@router.get(
    "/faq/{faq_id}",
    response_model=FaqPublicItem,
    summary="Вопрос/ответ по ID",
    responses=error_responses(404),
)
async def get_faq_entry(
    faq_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> FaqPublicItem:
    """Возвращает одну FAQ-запись по ID. Только активные записи."""
    svc = FaqPublicService(db)
    return await svc.get_by_id(faq_id)
