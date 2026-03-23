"""Public article endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.pagination import PaginatedResponse
from app.schemas.public import (
    ArticleDetailResponse,
    ArticleListItem,
    ArticleThemeListResponse,
)
from app.services.article_public_service import ArticlePublicService

router = APIRouter()


@router.get(
    "/articles",
    response_model=PaginatedResponse[ArticleListItem],
    summary="Список статей",
)
async def list_articles(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    theme_slug: str | None = Query(None, description="Фильтр по slug темы"),
    search: str | None = Query(None, min_length=2, description="Полнотекстовый поиск"),
) -> dict[str, Any]:
    """Пагинированный список опубликованных статей."""
    svc = ArticlePublicService(db)
    return await svc.list_articles(
        limit=limit, offset=offset, theme_slug=theme_slug, search=search,
    )


@router.get(
    "/article-themes",
    response_model=ArticleThemeListResponse,
    summary="Список тем статей",
)
async def list_article_themes(
    db: AsyncSession = Depends(get_db_session),
    active: bool | None = Query(None, description="Фильтр по активности"),
    has_articles: bool | None = Query(None, description="Только темы со статьями"),
) -> dict[str, Any]:
    """Список тем для фильтрации статей."""
    svc = ArticlePublicService(db)
    return await svc.list_article_themes(active=active, has_articles=has_articles)


@router.get(
    "/articles/{slug}",
    response_model=ArticleDetailResponse,
    summary="Статья по slug",
    responses=error_responses(404),
)
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> ArticleDetailResponse:
    """Полный текст статьи с метаданными и SEO.

    - **404** — статья не найдена
    """
    svc = ArticlePublicService(db)
    return await svc.get_article(slug)
