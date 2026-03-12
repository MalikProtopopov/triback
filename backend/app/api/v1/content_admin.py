"""Admin endpoints for content management (articles, themes, org documents)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.pagination import PaginatedResponse
from app.core.security import require_role
from app.schemas.content_admin import (
    ArticleAdminDetailResponse,
    ArticleAdminListItem,
    ArticleCreateRequest,
    ArticleUpdateRequest,
    OrgDocCreateRequest,
    OrgDocDetailResponse,
    OrgDocListItem,
    OrgDocUpdateRequest,
    ThemeAdminResponse,
    ThemeCreateRequest,
    ThemeUpdateRequest,
)
from app.services.content_service import ContentAdminService

router = APIRouter(prefix="/admin")

ADMIN_MANAGER = require_role("admin", "manager")
ADMIN_ONLY = require_role("admin")


# ══ Articles ══════════════════════════════════════════════════════

@router.get("/articles", response_model=PaginatedResponse[ArticleAdminListItem])
async def list_articles(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    theme_slug: str | None = Query(None),
) -> dict[str, Any]:
    svc = ContentAdminService(db)
    return await svc.list_articles(
        limit=limit, offset=offset, status=status, theme_slug=theme_slug,
    )


@router.post("/articles", response_model=ArticleAdminDetailResponse, status_code=201)
async def create_article(
    body: ArticleCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    cover_image: UploadFile | None = File(None),
) -> ArticleAdminDetailResponse:
    admin_id = UUID(payload["sub"])
    svc = ContentAdminService(db)
    return await svc.create_article(admin_id, body.model_dump(), cover_image)


@router.get("/articles/{article_id}", response_model=ArticleAdminDetailResponse)
async def get_article(
    article_id: UUID,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ArticleAdminDetailResponse:
    svc = ContentAdminService(db)
    return await svc.get_article(article_id)


@router.patch("/articles/{article_id}", response_model=ArticleAdminDetailResponse)
async def update_article(
    article_id: UUID,
    body: ArticleUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    cover_image: UploadFile | None = File(None),
) -> ArticleAdminDetailResponse:
    svc = ContentAdminService(db)
    return await svc.update_article(article_id, body.model_dump(exclude_none=True), cover_image)


@router.delete("/articles/{article_id}", status_code=204)
async def delete_article(
    article_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = ContentAdminService(db)
    await svc.delete_article(article_id)
    return Response(status_code=204)


# ══ Article Themes ════════════════════════════════════════════════

@router.get("/article-themes")
async def list_themes(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    active: bool | None = Query(None),
    has_articles: bool | None = Query(None),
) -> dict[str, Any]:
    svc = ContentAdminService(db)
    items = await svc.list_themes(active=active, has_articles=has_articles)
    return {"data": items}


@router.post("/article-themes", response_model=ThemeAdminResponse, status_code=201)
async def create_theme(
    body: ThemeCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ThemeAdminResponse:
    svc = ContentAdminService(db)
    return await svc.create_theme(body.model_dump())


@router.patch("/article-themes/{theme_id}", response_model=ThemeAdminResponse)
async def update_theme(
    theme_id: UUID,
    body: ThemeUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> ThemeAdminResponse:
    svc = ContentAdminService(db)
    return await svc.update_theme(theme_id, body.model_dump(exclude_none=True))


@router.delete("/article-themes/{theme_id}", status_code=204)
async def delete_theme(
    theme_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = ContentAdminService(db)
    await svc.delete_theme(theme_id)
    return Response(status_code=204)


# ══ Organization Documents ════════════════════════════════════════

@router.get("/organization-documents", response_model=PaginatedResponse[OrgDocListItem])
async def list_org_docs(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    svc = ContentAdminService(db)
    return await svc.list_org_docs(limit=limit, offset=offset)


@router.post(
    "/organization-documents",
    response_model=OrgDocDetailResponse,
    status_code=201,
)
async def create_org_doc(
    body: OrgDocCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    file: UploadFile | None = File(None),
) -> OrgDocDetailResponse:
    admin_id = UUID(payload["sub"])
    svc = ContentAdminService(db)
    return await svc.create_org_doc(admin_id, body.model_dump(), file)


@router.patch(
    "/organization-documents/{doc_id}",
    response_model=OrgDocDetailResponse,
)
async def update_org_doc(
    doc_id: UUID,
    body: OrgDocUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
    file: UploadFile | None = File(None),
) -> OrgDocDetailResponse:
    admin_id = UUID(payload["sub"])
    svc = ContentAdminService(db)
    return await svc.update_org_doc(doc_id, admin_id, body.model_dump(exclude_none=True), file)


@router.delete("/organization-documents/{doc_id}", status_code=204)
async def delete_org_doc(
    doc_id: UUID,
    payload: dict[str, Any] = ADMIN_ONLY,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = ContentAdminService(db)
    await svc.delete_org_doc(doc_id)
    return Response(status_code=204)
