"""Pydantic schemas for admin content management (articles, themes, org docs)."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ── Articles ──────────────────────────────────────────────────────

class ArticleCreateRequest(BaseModel):
    title: str = Field(max_length=500)
    slug: str | None = Field(None, max_length=500)
    content: str
    excerpt: str | None = None
    status: Literal["draft", "published", "archived"] = "draft"
    seo_title: str | None = Field(None, max_length=255)
    seo_description: str | None = None
    theme_ids: list[UUID] = []


class ArticleUpdateRequest(BaseModel):
    title: str | None = Field(None, max_length=500)
    slug: str | None = Field(None, max_length=500)
    content: str | None = None
    excerpt: str | None = None
    status: Literal["draft", "published", "archived"] | None = None
    seo_title: str | None = Field(None, max_length=255)
    seo_description: str | None = None
    theme_ids: list[UUID] | None = None


class ThemeNested(BaseModel):
    id: UUID
    slug: str
    title: str


class ArticleAdminListItem(BaseModel):
    id: UUID
    slug: str
    title: str
    excerpt: str | None = None
    status: str
    author_id: UUID
    published_at: datetime | None = None
    cover_image_url: str | None = None
    themes: list[ThemeNested] = []
    created_at: datetime


class ArticleAdminDetailResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    content: str
    excerpt: str | None = None
    cover_image_url: str | None = None
    status: str
    author_id: UUID
    published_at: datetime | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    themes: list[ThemeNested] = []
    content_blocks: list["ContentBlockNested"] = []
    created_at: datetime
    updated_at: datetime | None = None


# ── Article Themes ────────────────────────────────────────────────

class ThemeCreateRequest(BaseModel):
    title: str = Field(max_length=255)
    slug: str | None = Field(None, max_length=255)
    is_active: bool = True
    sort_order: int = 0


class ThemeUpdateRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    slug: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    sort_order: int | None = None


class ThemeAdminResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    is_active: bool
    sort_order: int
    articles_count: int = 0


class ThemeAdminListResponse(BaseModel):
    data: list[ThemeAdminResponse]


# ── Organization Documents ────────────────────────────────────────

class OrgDocCreateRequest(BaseModel):
    title: str = Field(max_length=500)
    slug: str | None = Field(None, max_length=255)
    content: str | None = None
    sort_order: int = 0
    is_active: bool = True


class OrgDocUpdateRequest(BaseModel):
    title: str | None = Field(None, max_length=500)
    slug: str | None = Field(None, max_length=255)
    content: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class OrgDocListItem(BaseModel):
    id: UUID
    title: str
    slug: str
    content: str | None = None
    file_url: str | None = None
    sort_order: int
    is_active: bool
    updated_at: datetime | None = None


class ContentBlockNested(BaseModel):
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


class OrgDocDetailResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    content: str | None = None
    file_url: str | None = None
    sort_order: int
    is_active: bool
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None
    content_blocks: list[ContentBlockNested] = []


class OrgDocReorderItem(BaseModel):
    id: UUID
    sort_order: int


class OrgDocReorderRequest(BaseModel):
    items: list[OrgDocReorderItem] = Field(min_length=1)
