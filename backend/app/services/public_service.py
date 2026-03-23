"""Public service — facade for backward compatibility.

Delegates to:
  - CityPublicService
  - DoctorCatalogService
  - EventPublicService
  - ArticlePublicService
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.article_public_service import ArticlePublicService
from app.services.city_public_service import CityPublicService
from app.services.doctor_catalog_service import DoctorCatalogService
from app.services.event_public_service import EventPublicService


class PublicService:
    """Thin facade — preserves the original API so any existing callers keep working."""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis
        self._cities = CityPublicService(db, redis)
        self._doctors = DoctorCatalogService(db)
        self._events = EventPublicService(db)
        self._articles = ArticlePublicService(db)

    # ── Cities ────────────────────────────────────────────────────

    async def list_cities(self, *, with_doctors: bool = False) -> dict[str, Any]:
        return await self._cities.list_cities(with_doctors=with_doctors)

    async def get_city(self, slug: str) -> Any:
        return await self._cities.get_city(slug)

    # ── Doctors ───────────────────────────────────────────────────

    async def list_doctors(
        self,
        *,
        limit: int = 12,
        offset: int = 0,
        city_id: UUID | None = None,
        city_slug: str | None = None,
        specialization: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        return await self._doctors.list_doctors(
            limit=limit, offset=offset, city_id=city_id,
            city_slug=city_slug, specialization=specialization, search=search,
        )

    async def get_doctor(self, identifier: str) -> Any:
        return await self._doctors.get_doctor(identifier)

    # ── Events ────────────────────────────────────────────────────

    async def list_events(
        self, *, limit: int = 20, offset: int = 0, period: str = "upcoming",
    ) -> dict[str, Any]:
        return await self._events.list_events(limit=limit, offset=offset, period=period)

    async def get_event(self, slug: str) -> Any:
        return await self._events.get_event(slug)

    # ── Articles ──────────────────────────────────────────────────

    async def list_articles(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        theme_slug: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        return await self._articles.list_articles(
            limit=limit, offset=offset, theme_slug=theme_slug, search=search,
        )

    async def list_article_themes(
        self, *, active: bool | None = None, has_articles: bool | None = None,
    ) -> dict[str, Any]:
        return await self._articles.list_article_themes(
            active=active, has_articles=has_articles,
        )

    async def get_article(self, slug: str) -> Any:
        return await self._articles.get_article(slug)
