"""Admin service for articles, article themes, organization documents."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import UploadFile
from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppValidationError, NotFoundError
from app.core.utils import generate_unique_slug
from app.models.content import (
    Article,
    ArticleTheme,
    ArticleThemeAssignment,
    OrganizationDocument,
)
from app.schemas.content_admin import (
    ArticleAdminDetailResponse,
    ArticleAdminListItem,
    OrgDocDetailResponse,
    OrgDocListItem,
    ThemeAdminResponse,
    ThemeNested,
)
from app.services import file_service

logger = structlog.get_logger(__name__)

DOCUMENT_MIMES = file_service.IMAGE_MIMES | {"application/pdf"}


class ContentAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ══ Articles ══════════════════════════════════════════════════

    async def list_articles(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        theme_slug: str | None = None,
    ) -> dict[str, Any]:
        base = (
            select(Article)
            .options(
                selectinload(Article.theme_assignments).selectinload(
                    ArticleThemeAssignment.theme
                )
            )
        )
        count_q = select(func.count(Article.id))

        if status:
            base = base.where(Article.status == status)
            count_q = count_q.where(Article.status == status)
        if theme_slug:
            base = base.join(ArticleThemeAssignment).join(ArticleTheme).where(
                ArticleTheme.slug == theme_slug
            )
            count_q = (
                count_q.join(ArticleThemeAssignment)
                .join(ArticleTheme)
                .where(ArticleTheme.slug == theme_slug)
            )

        total = (await self.db.execute(count_q)).scalar() or 0
        base = base.order_by(Article.created_at.desc()).offset(offset).limit(limit)
        rows = (await self.db.execute(base)).unique().scalars().all()

        items = [
            ArticleAdminListItem(
                id=a.id,
                slug=a.slug,
                title=a.title,
                excerpt=a.excerpt,
                status=a.status,
                author_id=a.author_id,
                published_at=a.published_at,
                cover_image_url=a.cover_image_url,
                themes=[
                    ThemeNested(id=ta.theme.id, slug=ta.theme.slug, title=ta.theme.title)
                    for ta in a.theme_assignments
                ],
                created_at=a.created_at,
            )
            for a in rows
        ]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    async def create_article(
        self,
        admin_id: UUID,
        data: dict[str, Any],
        cover_image: UploadFile | None = None,
    ) -> ArticleAdminDetailResponse:
        slug = await generate_unique_slug(self.db, Article, data["title"])

        cover_url: str | None = None
        if cover_image:
            cover_url = await file_service.upload_file(
                cover_image,
                path="articles/covers",
                allowed_types=file_service.IMAGE_MIMES,
                max_size_mb=5,
            )

        theme_ids: list[UUID] = data.pop("theme_ids", [])

        article = Article(
            title=data["title"],
            slug=slug,
            content=data["content"],
            excerpt=data.get("excerpt"),
            status=data.get("status", "draft"),
            author_id=admin_id,
            seo_title=data.get("seo_title"),
            seo_description=data.get("seo_description"),
            cover_image_url=cover_url,
        )

        if article.status == "published" and article.published_at is None:
            article.published_at = datetime.now(UTC)

        self.db.add(article)
        await self.db.flush()

        for tid in theme_ids:
            self.db.add(ArticleThemeAssignment(article_id=article.id, theme_id=tid))

        await self.db.commit()
        return await self.get_article(article.id)

    async def get_article(self, article_id: UUID) -> ArticleAdminDetailResponse:
        result = await self.db.execute(
            select(Article)
            .options(
                selectinload(Article.theme_assignments).selectinload(
                    ArticleThemeAssignment.theme
                )
            )
            .where(Article.id == article_id)
        )
        a = result.unique().scalar_one_or_none()
        if not a:
            raise NotFoundError("Article not found")

        return ArticleAdminDetailResponse(
            id=a.id,
            slug=a.slug,
            title=a.title,
            content=a.content,
            excerpt=a.excerpt,
            cover_image_url=a.cover_image_url,
            status=a.status,
            author_id=a.author_id,
            published_at=a.published_at,
            seo_title=a.seo_title,
            seo_description=a.seo_description,
            themes=[
                ThemeNested(id=ta.theme.id, slug=ta.theme.slug, title=ta.theme.title)
                for ta in a.theme_assignments
            ],
            created_at=a.created_at,
            updated_at=a.updated_at,
        )

    async def update_article(
        self,
        article_id: UUID,
        data: dict[str, Any],
        cover_image: UploadFile | None = None,
    ) -> ArticleAdminDetailResponse:
        result = await self.db.execute(
            select(Article)
            .options(selectinload(Article.theme_assignments))
            .where(Article.id == article_id)
        )
        article = result.unique().scalar_one_or_none()
        if not article:
            raise NotFoundError("Article not found")

        theme_ids: list[UUID] | None = data.pop("theme_ids", None)

        for field, value in data.items():
            if value is not None and hasattr(article, field):
                setattr(article, field, value)

        if article.status == "published" and article.published_at is None:
            article.published_at = datetime.now(UTC)

        if cover_image:
            if article.cover_image_url:
                await file_service.delete_file(article.cover_image_url)
            article.cover_image_url = await file_service.upload_file(
                cover_image,
                path="articles/covers",
                allowed_types=file_service.IMAGE_MIMES,
                max_size_mb=5,
            )

        if theme_ids is not None:
            for ta in list(article.theme_assignments):
                await self.db.delete(ta)
            await self.db.flush()
            for tid in theme_ids:
                self.db.add(ArticleThemeAssignment(article_id=article.id, theme_id=tid))

        await self.db.commit()
        return await self.get_article(article_id)

    async def delete_article(self, article_id: UUID) -> None:
        article = await self.db.get(Article, article_id)
        if not article:
            raise NotFoundError("Article not found")
        article.deleted_at = datetime.now(UTC)
        await self.db.commit()

    # ══ Article Themes ════════════════════════════════════════════

    async def list_themes(
        self, *, active: bool | None = None, has_articles: bool | None = None
    ) -> list[ThemeAdminResponse]:
        base = select(ArticleTheme)

        if active is True:
            base = base.where(ArticleTheme.is_active.is_(True))
        elif active is False:
            base = base.where(ArticleTheme.is_active.is_(False))

        if has_articles is True:
            base = base.where(
                exists(
                    select(ArticleThemeAssignment.id)
                    .join(Article, ArticleThemeAssignment.article_id == Article.id)
                    .where(
                        and_(
                            ArticleThemeAssignment.theme_id == ArticleTheme.id,
                            Article.status == "published",
                        )
                    )
                )
            )

        base = base.order_by(ArticleTheme.sort_order, ArticleTheme.title)
        rows = (await self.db.execute(base)).scalars().all()

        result: list[ThemeAdminResponse] = []
        for t in rows:
            count = (
                await self.db.execute(
                    select(func.count(ArticleThemeAssignment.id)).where(
                        ArticleThemeAssignment.theme_id == t.id
                    )
                )
            ).scalar() or 0
            result.append(
                ThemeAdminResponse(
                    id=t.id,
                    slug=t.slug,
                    title=t.title,
                    is_active=t.is_active,
                    sort_order=t.sort_order,
                    articles_count=count,
                )
            )
        return result

    async def create_theme(self, data: dict[str, Any]) -> ThemeAdminResponse:
        slug = data.get("slug") or ""
        if not slug:
            slug = await generate_unique_slug(self.db, ArticleTheme, data["title"])
        theme = ArticleTheme(
            title=data["title"],
            slug=slug,
            is_active=data.get("is_active", True),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(theme)
        await self.db.commit()
        await self.db.refresh(theme)
        return ThemeAdminResponse(
            id=theme.id,
            slug=theme.slug,
            title=theme.title,
            is_active=theme.is_active,
            sort_order=theme.sort_order,
            articles_count=0,
        )

    async def update_theme(
        self, theme_id: UUID, data: dict[str, Any]
    ) -> ThemeAdminResponse:
        theme = await self.db.get(ArticleTheme, theme_id)
        if not theme:
            raise NotFoundError("Theme not found")

        for field, value in data.items():
            if value is not None and hasattr(theme, field):
                setattr(theme, field, value)

        await self.db.commit()
        await self.db.refresh(theme)

        count = (
            await self.db.execute(
                select(func.count(ArticleThemeAssignment.id)).where(
                    ArticleThemeAssignment.theme_id == theme.id
                )
            )
        ).scalar() or 0

        return ThemeAdminResponse(
            id=theme.id,
            slug=theme.slug,
            title=theme.title,
            is_active=theme.is_active,
            sort_order=theme.sort_order,
            articles_count=count,
        )

    async def delete_theme(self, theme_id: UUID) -> None:
        theme = await self.db.get(ArticleTheme, theme_id)
        if not theme:
            raise NotFoundError("Theme not found")

        published_linked = (
            await self.db.execute(
                select(func.count(ArticleThemeAssignment.id))
                .join(Article, ArticleThemeAssignment.article_id == Article.id)
                .where(
                    and_(
                        ArticleThemeAssignment.theme_id == theme_id,
                        Article.status == "published",
                    )
                )
            )
        ).scalar() or 0

        if published_linked > 0:
            raise AppValidationError(
                "Невозможно удалить тему с привязанными опубликованными статьями"
            )

        await self.db.delete(theme)
        await self.db.commit()

    # ══ Organization Documents ════════════════════════════════════

    async def list_org_docs(
        self, *, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        count_q = select(func.count(OrganizationDocument.id))
        total = (await self.db.execute(count_q)).scalar() or 0

        base = (
            select(OrganizationDocument)
            .order_by(OrganizationDocument.sort_order, OrganizationDocument.title)
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.db.execute(base)).scalars().all()

        items = [
            OrgDocListItem(
                id=d.id,
                title=d.title,
                slug=d.slug,
                file_url=d.file_url,
                sort_order=d.sort_order,
                is_active=d.is_active,
                updated_at=d.updated_at,
            )
            for d in rows
        ]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    async def create_org_doc(
        self,
        admin_id: UUID,
        data: dict[str, Any],
        file: UploadFile | None = None,
    ) -> OrgDocDetailResponse:
        slug = await generate_unique_slug(self.db, OrganizationDocument, data["title"])

        file_url: str | None = None
        if file:
            file_url = await file_service.upload_file(
                file,
                path="organization-documents",
                allowed_types=DOCUMENT_MIMES,
                max_size_mb=20,
            )

        doc = OrganizationDocument(
            title=data["title"],
            slug=slug,
            content=data.get("content"),
            file_url=file_url,
            sort_order=data.get("sort_order", 0),
            is_active=data.get("is_active", True),
            updated_by=admin_id,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return self._org_doc_detail(doc)

    async def update_org_doc(
        self,
        doc_id: UUID,
        admin_id: UUID,
        data: dict[str, Any],
        file: UploadFile | None = None,
    ) -> OrgDocDetailResponse:
        doc = await self.db.get(OrganizationDocument, doc_id)
        if not doc:
            raise NotFoundError("Document not found")

        for field, value in data.items():
            if value is not None and hasattr(doc, field):
                setattr(doc, field, value)

        if file:
            if doc.file_url:
                await file_service.delete_file(doc.file_url)
            doc.file_url = await file_service.upload_file(
                file,
                path="organization-documents",
                allowed_types=DOCUMENT_MIMES,
                max_size_mb=20,
            )

        doc.updated_by = admin_id
        await self.db.commit()
        await self.db.refresh(doc)
        return self._org_doc_detail(doc)

    async def delete_org_doc(self, doc_id: UUID) -> None:
        doc = await self.db.get(OrganizationDocument, doc_id)
        if not doc:
            raise NotFoundError("Document not found")

        if doc.file_url:
            await file_service.delete_file(doc.file_url)

        await self.db.delete(doc)
        await self.db.commit()

    async def reorder_org_docs(
        self, items: list[dict[str, Any]]
    ) -> list[OrgDocDetailResponse]:
        result = []
        for item in items:
            doc = await self.db.get(OrganizationDocument, item["id"])
            if not doc:
                raise NotFoundError(f"Document {item['id']} not found")
            doc.sort_order = item["sort_order"]
            result.append(doc)
        await self.db.commit()
        return [
            self._org_doc_detail(d)
            for d in sorted(result, key=lambda d: d.sort_order)
        ]

    def _org_doc_detail(self, d: OrganizationDocument) -> OrgDocDetailResponse:
        return OrgDocDetailResponse(
            id=d.id,
            title=d.title,
            slug=d.slug,
            content=d.content,
            file_url=d.file_url,
            sort_order=d.sort_order,
            is_active=d.is_active,
            updated_by=d.updated_by,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
