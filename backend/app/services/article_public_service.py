"""Public article service — list and detail for guest access."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ArticleStatus
from app.core.exceptions import NotFoundError
from app.models.content import Article, ArticleTheme, ArticleThemeAssignment
from app.schemas.public import (
    ArticleDetailResponse,
    ArticleListItem,
    ArticleThemeResponse,
    ContentBlockPublicNested,
    SeoNested,
)
from app.schemas.shared import ThemeNested
from app.services import file_service
from app.services.content_block_service import list_blocks_for_entity


class ArticlePublicService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_articles(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        theme_slug: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        base = (
            select(Article)
            .options(selectinload(Article.theme_assignments).joinedload(ArticleThemeAssignment.theme))
            .where(Article.status == ArticleStatus.PUBLISHED)
        )
        count_q = select(func.count(Article.id)).where(Article.status == ArticleStatus.PUBLISHED)

        if theme_slug:
            base = base.join(ArticleThemeAssignment).join(ArticleTheme).where(
                ArticleTheme.slug == theme_slug
            )
            count_q = count_q.join(ArticleThemeAssignment).join(ArticleTheme).where(
                ArticleTheme.slug == theme_slug
            )
        if search and len(search) >= 2:
            base = base.where(Article.title.ilike(f"%{search}%"))
            count_q = count_q.where(Article.title.ilike(f"%{search}%"))

        total = (await self.db.execute(count_q)).scalar() or 0
        base = base.order_by(Article.published_at.desc()).offset(offset).limit(limit)
        rows = (await self.db.execute(base)).unique().scalars().all()

        items = [
            ArticleListItem(
                id=a.id, slug=a.slug, title=a.title, excerpt=a.excerpt,
                cover_image_url=file_service.build_media_url(a.cover_image_url),
                published_at=a.published_at,
                themes=[
                    ThemeNested(id=ta.theme.id, slug=ta.theme.slug, title=ta.theme.title)
                    for ta in a.theme_assignments
                ],
            )
            for a in rows
        ]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    async def list_article_themes(
        self, *, active: bool | None = None, has_articles: bool | None = None
    ) -> dict[str, Any]:
        base = select(ArticleTheme)

        if active is True:
            base = base.where(ArticleTheme.is_active.is_(True))
        elif active is False:
            base = base.where(ArticleTheme.is_active.is_(False))

        if has_articles is True:
            published_exists = exists(
                select(ArticleThemeAssignment.id)
                .join(Article, ArticleThemeAssignment.article_id == Article.id)
                .where(
                    and_(
                        ArticleThemeAssignment.theme_id == ArticleTheme.id,
                        Article.status == ArticleStatus.PUBLISHED,
                    )
                )
            )
            base = base.where(published_exists)

        base = base.order_by(ArticleTheme.sort_order, ArticleTheme.title)
        rows = (await self.db.execute(base)).scalars().all()
        items = [ArticleThemeResponse(id=t.id, slug=t.slug, title=t.title) for t in rows]
        return {"data": items}

    async def get_article(self, slug: str) -> ArticleDetailResponse:
        result = await self.db.execute(
            select(Article)
            .options(selectinload(Article.theme_assignments).joinedload(ArticleThemeAssignment.theme))
            .where(and_(Article.slug == slug, Article.status == ArticleStatus.PUBLISHED))
        )
        article = result.unique().scalar_one_or_none()
        if not article:
            raise NotFoundError("Article not found")

        seo_title = article.seo_title or f"{article.title} | РОТА"
        seo_desc = article.seo_description or article.excerpt or article.title

        seo = SeoNested(
            title=seo_title, description=seo_desc, og_type="article",
            og_image=file_service.build_media_url(article.cover_image_url),
            twitter_card="summary_large_image",
        )

        blocks = await list_blocks_for_entity(self.db, "article", article.id)
        content_blocks = [
            ContentBlockPublicNested(
                id=str(b.id), block_type=b.block_type, sort_order=b.sort_order,
                title=b.title, content=b.content,
                media_url=file_service.build_media_url(b.media_url),
                thumbnail_url=file_service.build_media_url(b.thumbnail_url),
                link_url=b.link_url, link_label=b.link_label, device_type=b.device_type,
            )
            for b in blocks
        ]

        return ArticleDetailResponse(
            id=article.id, slug=article.slug, title=article.title,
            content=article.content, excerpt=article.excerpt,
            cover_image_url=file_service.build_media_url(article.cover_image_url),
            published_at=article.published_at,
            themes=[
                ThemeNested(id=ta.theme.id, slug=ta.theme.slug, title=ta.theme.title)
                for ta in article.theme_assignments
            ],
            seo=seo, content_blocks=content_blocks,
        )
