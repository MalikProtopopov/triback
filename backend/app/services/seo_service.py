"""SEO service — CRUD for PageSeo records."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppValidationError, NotFoundError
from app.models.content import PageSeo
from app.schemas.seo import SeoPageCreate, SeoPageResponse, SeoPageUpdate
from app.services import file_service


class SeoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_pages(
        self, *, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        total = (
            await self.db.execute(select(func.count(PageSeo.id)))
        ).scalar() or 0
        rows = (
            await self.db.execute(
                select(PageSeo).order_by(PageSeo.slug).offset(offset).limit(limit)
            )
        ).scalars().all()
        return {
            "data": [self._to_response(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_by_slug(self, slug: str) -> SeoPageResponse:
        page = await self._find_by_slug(slug)
        return self._to_response(page)

    async def create(self, body: SeoPageCreate) -> SeoPageResponse:
        existing = (
            await self.db.execute(
                select(PageSeo).where(PageSeo.slug == body.slug)
            )
        ).scalar_one_or_none()
        if existing:
            raise AppValidationError(f"SEO page with slug '{body.slug}' already exists")

        page = PageSeo(**body.model_dump())
        self.db.add(page)
        await self.db.commit()
        await self.db.refresh(page)
        return self._to_response(page)

    async def update(self, slug: str, body: SeoPageUpdate) -> SeoPageResponse:
        page = await self._find_by_slug(slug)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(page, field, value)
        await self.db.commit()
        await self.db.refresh(page)
        return self._to_response(page)

    async def delete(self, slug: str) -> None:
        page = await self._find_by_slug(slug)
        await self.db.delete(page)
        await self.db.commit()

    async def _find_by_slug(self, slug: str) -> PageSeo:
        result = await self.db.execute(
            select(PageSeo).where(PageSeo.slug == slug)
        )
        page = result.scalar_one_or_none()
        if not page:
            raise NotFoundError(f"SEO page '{slug}' not found")
        return page

    @staticmethod
    def _to_response(page: PageSeo) -> SeoPageResponse:
        return SeoPageResponse(
            id=page.id,
            slug=page.slug,
            title=page.title,
            description=page.description,
            og_title=page.og_title,
            og_description=page.og_description,
            og_image_url=file_service.build_media_url(page.og_image_url),
            og_url=page.og_url,
            og_type=page.og_type,
            twitter_card=page.twitter_card,
            canonical_url=page.canonical_url,
            custom_meta=page.custom_meta,
            updated_at=page.updated_at,
        )
