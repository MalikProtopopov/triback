"""Public organization document endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.core.openapi import error_responses
from app.models.content import ContentBlock, OrganizationDocument
from app.schemas.public import (
    ContentBlockPublicNested,
    OrgDocPublicDetailResponse,
    OrgDocPublicListResponse,
)
from app.services import file_service

router = APIRouter()


@router.get(
    "/organization-documents",
    response_model=OrgDocPublicListResponse,
    summary="Документы организации",
)
async def list_organization_documents(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Список активных документов организации (устав, положения и т.д.)."""
    result = await db.execute(
        select(OrganizationDocument)
        .where(OrganizationDocument.is_active.is_(True))
        .order_by(OrganizationDocument.sort_order)
    )
    docs = result.scalars().all()
    return {
        "data": [
            {
                "id": str(d.id),
                "title": d.title,
                "slug": d.slug,
                "content": d.content,
                "file_url": file_service.build_media_url(d.file_url),
            }
            for d in docs
        ]
    }


@router.get(
    "/organization-documents/{slug}",
    response_model=OrgDocPublicDetailResponse,
    summary="Документ организации по slug",
    responses=error_responses(404),
)
async def get_organization_document(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> OrgDocPublicDetailResponse:
    """Детальная страница документа организации по slug.

    - **404** — документ не найден
    """
    result = await db.execute(
        select(OrganizationDocument).where(
            OrganizationDocument.slug == slug,
            OrganizationDocument.is_active.is_(True),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document not found")

    blocks_result = await db.execute(
        select(ContentBlock)
        .where(
            ContentBlock.entity_type == "organization_document",
            ContentBlock.entity_id == doc.id,
        )
        .order_by(ContentBlock.sort_order.asc())
    )
    blocks = blocks_result.scalars().all()

    return OrgDocPublicDetailResponse(
        id=str(doc.id),
        title=doc.title,
        slug=doc.slug,
        content=doc.content,
        file_url=file_service.build_media_url(doc.file_url),
        content_blocks=[
            ContentBlockPublicNested(
                id=str(b.id),
                block_type=b.block_type,
                sort_order=b.sort_order,
                title=b.title,
                content=b.content,
                media_url=file_service.build_media_url(b.media_url),
                thumbnail_url=file_service.build_media_url(b.thumbnail_url),
                link_url=b.link_url,
                link_label=b.link_label,
                device_type=b.device_type,
            )
            for b in blocks
        ],
    )
