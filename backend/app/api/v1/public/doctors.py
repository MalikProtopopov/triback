"""Public doctor catalog endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.pagination import PaginatedResponse
from app.schemas.public import DoctorPublicDetailResponse, DoctorPublicListItem
from app.services.doctor_catalog_service import DoctorCatalogService

router = APIRouter()


@router.get(
    "/doctors",
    response_model=PaginatedResponse[DoctorPublicListItem],
    summary="Каталог врачей",
)
async def list_doctors(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(12, ge=1, le=50),
    offset: int = Query(0, ge=0),
    city_id: UUID | None = Query(None, description="Фильтр по UUID города"),
    city_slug: str | None = Query(None, description="Фильтр по slug города"),
    specialization: str | None = Query(None),
    board_role: list[str] | None = Query(None, description="pravlenie, president"),
    search: str | None = Query(None, min_length=2, description="Поиск по ФИО (мин. 2 символа)"),
) -> dict[str, Any]:
    """Пагинированный список активных врачей с фильтрацией."""
    svc = DoctorCatalogService(db)
    return await svc.list_doctors(
        limit=limit, offset=offset, city_id=city_id,
        city_slug=city_slug, specialization=specialization,
        board_role=board_role, search=search,
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
) -> DoctorPublicDetailResponse:
    """Детальная карточка врача по UUID или slug.

    - **404** — врач не найден или неактивен
    """
    svc = DoctorCatalogService(db)
    return await svc.get_doctor(identifier)
