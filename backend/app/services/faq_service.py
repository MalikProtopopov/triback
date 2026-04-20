"""Service layer for FAQ entries — public & admin operations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.faq import FaqEntry
from app.schemas.faq import (
    FaqAdminItem,
    FaqCreateRequest,
    FaqPublicItem,
    FaqUpdateRequest,
)


class FaqPublicService:
    """Read-only access to active FAQ entries for the public site."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        answered_only: bool = False,
    ) -> dict[str, Any]:
        base = select(FaqEntry).where(FaqEntry.is_active.is_(True))
        count_q = select(func.count(FaqEntry.id)).where(FaqEntry.is_active.is_(True))

        if answered_only:
            cond = FaqEntry.answer_text.isnot(None) & (FaqEntry.answer_text != "")
            base = base.where(cond)
            count_q = count_q.where(cond)

        if search and len(search) >= 2:
            like = f"%{search}%"
            search_cond = FaqEntry.question_title.ilike(like) | FaqEntry.question_text.ilike(like)
            base = base.where(search_cond)
            count_q = count_q.where(search_cond)

        total: int = (await self.db.execute(count_q)).scalar() or 0
        rows = (
            await self.db.execute(
                base.order_by(FaqEntry.original_date.desc().nullslast(), FaqEntry.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()

        return {
            "data": [_to_public(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_by_id(self, faq_id: UUID) -> FaqPublicItem:
        entry = await self._fetch(faq_id, active_only=True)
        return _to_public(entry)

    async def _fetch(self, faq_id: UUID, *, active_only: bool = False) -> FaqEntry:
        q = select(FaqEntry).where(FaqEntry.id == faq_id)
        if active_only:
            q = q.where(FaqEntry.is_active.is_(True))
        result = await self.db.execute(q)
        entry = result.scalar_one_or_none()
        if not entry:
            raise NotFoundError("FAQ entry not found")
        return entry


class FaqAdminService:
    """Full CRUD for admin panel."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        base = select(FaqEntry)
        count_q = select(func.count(FaqEntry.id))

        if is_active is not None:
            base = base.where(FaqEntry.is_active == is_active)
            count_q = count_q.where(FaqEntry.is_active == is_active)

        if search and len(search) >= 2:
            like = f"%{search}%"
            cond = FaqEntry.question_title.ilike(like) | FaqEntry.question_text.ilike(like)
            base = base.where(cond)
            count_q = count_q.where(cond)

        total: int = (await self.db.execute(count_q)).scalar() or 0
        rows = (
            await self.db.execute(
                base.order_by(FaqEntry.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()

        return {
            "data": [_to_admin(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_by_id(self, faq_id: UUID) -> FaqAdminItem:
        entry = await self._fetch(faq_id)
        return _to_admin(entry)

    async def create(self, body: FaqCreateRequest) -> FaqAdminItem:
        entry = FaqEntry(**body.model_dump())
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return _to_admin(entry)

    async def update(self, faq_id: UUID, body: FaqUpdateRequest) -> FaqAdminItem:
        entry = await self._fetch(faq_id)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(entry, field, value)
        await self.db.commit()
        await self.db.refresh(entry)
        return _to_admin(entry)

    async def delete(self, faq_id: UUID) -> None:
        entry = await self._fetch(faq_id)
        await self.db.delete(entry)
        await self.db.commit()

    async def _fetch(self, faq_id: UUID) -> FaqEntry:
        result = await self.db.execute(select(FaqEntry).where(FaqEntry.id == faq_id))
        entry = result.scalar_one_or_none()
        if not entry:
            raise NotFoundError("FAQ entry not found")
        return entry


# ── Mappers ───────────────────────────────────────────────────────────


def _to_public(e: FaqEntry) -> FaqPublicItem:
    return FaqPublicItem(
        id=e.id,
        question_title=e.question_title,
        question_text=e.question_text,
        answer_text=e.answer_text,
        author_name=e.author_name,
        original_date=e.original_date,
    )


def _to_admin(e: FaqEntry) -> FaqAdminItem:
    return FaqAdminItem(
        id=e.id,
        question_title=e.question_title,
        question_text=e.question_text,
        answer_text=e.answer_text,
        author_name=e.author_name,
        is_active=e.is_active,
        original_date=e.original_date,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )
