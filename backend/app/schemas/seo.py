"""Pydantic schemas for SEO page meta admin endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SeoPageCreate(BaseModel):
    slug: str = Field(max_length=255)
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    og_title: str | None = Field(None, max_length=255)
    og_description: str | None = None
    og_image_url: str | None = Field(None, max_length=500)
    og_url: str | None = Field(None, max_length=500)
    og_type: str | None = Field(None, max_length=50)
    twitter_card: str | None = Field(None, max_length=50)
    canonical_url: str | None = Field(None, max_length=500)
    custom_meta: dict | None = None


class SeoPageUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    og_title: str | None = Field(None, max_length=255)
    og_description: str | None = None
    og_image_url: str | None = Field(None, max_length=500)
    og_url: str | None = Field(None, max_length=500)
    og_type: str | None = Field(None, max_length=50)
    twitter_card: str | None = Field(None, max_length=50)
    canonical_url: str | None = Field(None, max_length=500)
    custom_meta: dict | None = None


class SeoPageResponse(BaseModel):
    id: UUID
    slug: str
    title: str | None = None
    description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image_url: str | None = None
    og_url: str | None = None
    og_type: str | None = None
    twitter_card: str | None = None
    canonical_url: str | None = None
    custom_meta: dict | None = None
    updated_at: datetime
