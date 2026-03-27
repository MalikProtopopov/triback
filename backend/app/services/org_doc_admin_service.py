"""Admin service for organization documents."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.utils import generate_unique_slug
from app.models.content import ContentBlock, OrganizationDocument
from app.schemas.content_admin import OrgDocDetailResponse, OrgDocListItem
from app.schemas.shared import block_to_nested
from app.services import file_service

DOCUMENT_MIMES = file_service.IMAGE_MIMES | {"application/pdf"}


class OrgDocAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_docs(
        self, *, limit: int = 20, offset: int = 0,
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
                id=d.id, title=d.title, slug=d.slug, content=d.content,
                file_url=file_service.build_media_url(d.file_url),
                sort_order=d.sort_order, is_active=d.is_active,
                updated_at=d.updated_at,
            )
            for d in rows
        ]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    async def create(
        self, admin_id: UUID, data: dict[str, Any], file: UploadFile | None = None,
    ) -> OrgDocDetailResponse:
        slug = data.pop("slug", None) or await generate_unique_slug(
            self.db, OrganizationDocument, data["title"]
        )

        file_url: str | None = None
        if file:
            file_url = await file_service.upload_file(
                file, path="organization-documents",
                allowed_types=DOCUMENT_MIMES, max_size_mb=20,
            )

        doc = OrganizationDocument(
            title=data["title"], slug=slug,
            content=data.get("content"), file_url=file_url,
            sort_order=data.get("sort_order", 0),
            is_active=data.get("is_active", True),
            updated_by=admin_id,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return await self._detail(doc)

    async def update(
        self,
        doc_id: UUID,
        admin_id: UUID,
        data: dict[str, Any],
        file: UploadFile | None = None,
        remove_file: bool = False,
    ) -> OrgDocDetailResponse:
        doc = await self.db.get(OrganizationDocument, doc_id)
        if not doc:
            raise NotFoundError("Document not found")

        for field, value in data.items():
            if value is not None and hasattr(doc, field):
                setattr(doc, field, value)

        if remove_file and not file and doc.file_url:
            await file_service.delete_file(doc.file_url)
            doc.file_url = None
        elif file:
            if doc.file_url:
                await file_service.delete_file(doc.file_url)
            doc.file_url = await file_service.upload_file(
                file, path="organization-documents",
                allowed_types=DOCUMENT_MIMES, max_size_mb=20,
            )

        doc.updated_by = admin_id
        await self.db.commit()
        await self.db.refresh(doc)
        return await self._detail(doc)

    async def delete(self, doc_id: UUID) -> None:
        doc = await self.db.get(OrganizationDocument, doc_id)
        if not doc:
            raise NotFoundError("Document not found")
        if doc.file_url:
            await file_service.delete_file(doc.file_url)
        await self.db.delete(doc)
        await self.db.commit()

    async def reorder(
        self, items: list[dict[str, Any]],
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
            await self._detail(d)
            for d in sorted(result, key=lambda d: d.sort_order)
        ]

    async def _detail(self, d: OrganizationDocument) -> OrgDocDetailResponse:
        blocks_q = (
            select(ContentBlock)
            .where(
                ContentBlock.entity_type == "organization_document",
                ContentBlock.entity_id == d.id,
            )
            .order_by(ContentBlock.sort_order.asc())
        )
        blocks = (await self.db.execute(blocks_q)).scalars().all()
        return OrgDocDetailResponse(
            id=d.id, title=d.title, slug=d.slug, content=d.content,
            file_url=file_service.build_media_url(d.file_url),
            sort_order=d.sort_order, is_active=d.is_active,
            updated_by=d.updated_by,
            created_at=d.created_at, updated_at=d.updated_at,
            content_blocks=[block_to_nested(b) for b in blocks],
        )
