"""Public SEO metadata endpoint."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.schemas.seo import SeoPageResponse

router = APIRouter()


@router.get(
    "/seo/{slug}",
    response_model=SeoPageResponse,
    summary="SEO-метаданные страницы",
    responses=error_responses(404),
)
async def get_seo_page(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Возвращает SEO-метатеги для указанной страницы по slug.

    - **404** — SEO-страница не найдена
    """
    from app.services.seo_service import SeoService

    svc = SeoService(db)
    return (await svc.get_by_slug(slug)).model_dump()
