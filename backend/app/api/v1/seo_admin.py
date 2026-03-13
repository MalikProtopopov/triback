"""Admin endpoints for SEO page meta management."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.schemas.seo import SeoPageCreate, SeoPagePaginatedResponse, SeoPageResponse, SeoPageUpdate
from app.services.seo_service import SeoService

router = APIRouter(prefix="/admin")

ADMIN_MANAGER = require_role("admin", "manager")


@router.get(
    "/seo-pages",
    response_model=SeoPagePaginatedResponse,
    summary="Список SEO-страниц",
    responses=error_responses(401, 403),
)
async def list_seo_pages(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Пагинированный список всех SEO-страниц.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    svc = SeoService(db)
    return await svc.list_pages(limit=limit, offset=offset)


@router.get(
    "/seo-pages/{slug}",
    response_model=SeoPageResponse,
    summary="SEO-страница по slug",
    responses=error_responses(401, 403, 404),
)
async def get_seo_page(
    slug: str,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> SeoPageResponse:
    """Детальная информация об SEO-странице.

    - **404** — страница не найдена
    """
    svc = SeoService(db)
    return await svc.get_by_slug(slug)


@router.post(
    "/seo-pages",
    response_model=SeoPageResponse,
    status_code=201,
    summary="Создать SEO-страницу",
    responses=error_responses(401, 403, 409, 422),
)
async def create_seo_page(
    body: SeoPageCreate,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> SeoPageResponse:
    """Создаёт SEO-запись для страницы по slug.

    - **409** — страница с таким slug уже существует
    """
    svc = SeoService(db)
    return await svc.create(body)


@router.patch(
    "/seo-pages/{slug}",
    response_model=SeoPageResponse,
    summary="Обновить SEO-страницу",
    responses=error_responses(401, 403, 404, 422),
)
async def update_seo_page(
    slug: str,
    body: SeoPageUpdate,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> SeoPageResponse:
    """Обновляет метаданные SEO-страницы.

    - **404** — страница не найдена
    """
    svc = SeoService(db)
    return await svc.update(slug, body)


@router.delete(
    "/seo-pages/{slug}",
    status_code=204,
    summary="Удалить SEO-страницу",
    responses=error_responses(401, 403, 404),
)
async def delete_seo_page(
    slug: str,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Удаляет SEO-запись по slug.

    - **404** — страница не найдена
    """
    svc = SeoService(db)
    await svc.delete(slug)
