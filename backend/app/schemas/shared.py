"""Shared nested schemas and mapper helpers.

Single source of truth for nested DTO types used across admin,
profile, and public endpoints.  Import from here instead of
re-defining in each schema module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.services import file_service

# ── Nested schemas ────────────────────────────────────────────────


class CityNested(BaseModel):
    id: UUID
    name: str


class ThemeNested(BaseModel):
    id: UUID
    slug: str
    title: str


class SubscriptionNested(BaseModel):
    id: UUID | None = None
    status: str | None = None
    plan_name: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class PaymentNested(BaseModel):
    id: UUID
    amount: float
    product_type: str
    status: str
    paid_at: datetime | None = None
    created_at: datetime


class ContentBlockNested(BaseModel):
    """Admin-facing content block (includes metadata)."""
    id: UUID
    block_type: str
    sort_order: int
    title: str | None = None
    content: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    link_url: str | None = None
    link_label: str | None = None
    device_type: str
    block_metadata: dict[str, Any] | None = None


class ContentBlockPublicNested(BaseModel):
    """Public-facing content block; ``block_metadata`` URLs are fully resolved."""
    id: str
    block_type: str
    sort_order: int
    title: str | None = None
    content: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    link_url: str | None = None
    link_label: str | None = None
    device_type: str
    block_metadata: dict[str, Any] | None = None


# ── Mapper helpers ────────────────────────────────────────────────


def city_to_nested(city: Any) -> CityNested | None:
    if city is None:
        return None
    return CityNested(id=city.id, name=city.name)


def subscription_to_nested(sub: Any) -> SubscriptionNested | None:
    if sub is None:
        return None
    return SubscriptionNested(
        id=sub.id,
        status=sub.status,
        plan_name=sub.plan.name if getattr(sub, "plan", None) else None,
        starts_at=sub.starts_at,
        ends_at=sub.ends_at,
    )


def payment_to_nested(p: Any) -> PaymentNested:
    return PaymentNested(
        id=p.id,
        amount=float(p.amount),
        product_type=p.product_type,
        status=p.status,
        paid_at=p.paid_at,
        created_at=p.created_at,
    )


def theme_to_nested(theme_assoc: Any) -> ThemeNested:
    """Map an article-theme association (with ``.theme`` relation) to nested DTO."""
    t = theme_assoc.theme if hasattr(theme_assoc, "theme") else theme_assoc
    return ThemeNested(id=t.id, slug=t.slug, title=t.title)


def block_to_nested(b: Any) -> ContentBlockNested:
    return ContentBlockNested(
        id=b.id,
        block_type=b.block_type,
        sort_order=b.sort_order,
        title=b.title,
        content=b.content,
        media_url=file_service.build_media_url(b.media_url),
        thumbnail_url=file_service.build_media_url(b.thumbnail_url),
        link_url=b.link_url,
        link_label=b.link_label,
        device_type=b.device_type,
        block_metadata=file_service.enrich_block_metadata_urls(
            b.block_metadata, b.block_type
        ),
    )


def content_block_to_public(b: Any) -> ContentBlockPublicNested:
    """Map a :class:`~app.models.content.ContentBlock` row to the public DTO."""
    return ContentBlockPublicNested(
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
        block_metadata=file_service.enrich_block_metadata_urls(
            b.block_metadata, b.block_type
        ),
    )


def block_to_public_nested(b: Any) -> ContentBlockPublicNested:
    return content_block_to_public(b)
