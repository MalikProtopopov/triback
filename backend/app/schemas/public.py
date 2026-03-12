"""Pydantic schemas for public (guest) API endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

# ── SEO ───────────────────────────────────────────────────────────

class SeoNested(BaseModel):
    title: str | None = None
    description: str | None = None
    og_url: str | None = None
    og_type: str | None = None
    og_image: str | None = None
    twitter_card: str | None = "summary_large_image"
    canonical_url: str | None = None


# ── Cities ────────────────────────────────────────────────────────

class CityResponse(BaseModel):
    id: UUID
    name: str
    slug: str


class CityWithDoctorsResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    doctors_count: int


# ── Doctors (public) ──────────────────────────────────────────────

class DoctorPublicListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None = None
    city: str | None = None
    clinic_name: str | None = None
    specialization: str | None = None
    academic_degree: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    public_phone: str | None = None
    public_email: str | None = None
    slug: str | None = None


class DoctorPublicDetailResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None = None
    city: str | None = None
    clinic_name: str | None = None
    position: str | None = None
    specialization: str | None = None
    academic_degree: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    public_phone: str | None = None
    public_email: str | None = None
    slug: str | None = None
    seo: SeoNested | None = None


# ── Events ────────────────────────────────────────────────────────

class TariffPublicNested(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    conditions: str | None = None
    details: str | None = None
    price: float
    member_price: float
    benefits: list[Any] | None = None
    seats_limit: int | None = None
    seats_available: int | None = None


class EventPublicListItem(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str | None = None
    event_date: datetime
    event_end_date: datetime | None = None
    location: str | None = None
    cover_image_url: str | None = None
    tariffs: list[TariffPublicNested] = []
    status: str


class PreviewPhotoNested(BaseModel):
    thumbnail_url: str | None = None


class GalleryPublicNested(BaseModel):
    id: UUID
    title: str
    access_level: str
    photos_count: int = 0
    preview_photos: list[PreviewPhotoNested] = []


class RecordingPublicNested(BaseModel):
    id: UUID
    title: str
    video_source: str
    duration_seconds: int | None = None
    access_level: str


class EventPublicDetailResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str | None = None
    event_date: datetime
    event_end_date: datetime | None = None
    location: str | None = None
    cover_image_url: str | None = None
    tariffs: list[TariffPublicNested] = []
    galleries: list[GalleryPublicNested] = []
    recordings: list[RecordingPublicNested] = []
    seo: SeoNested | None = None


# ── Articles ──────────────────────────────────────────────────────

class ThemeNested(BaseModel):
    id: UUID
    slug: str
    title: str


class ArticleListItem(BaseModel):
    id: UUID
    slug: str
    title: str
    excerpt: str | None = None
    cover_image_url: str | None = None
    published_at: datetime | None = None
    themes: list[ThemeNested] = []


class ArticleDetailResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    content: str
    excerpt: str | None = None
    cover_image_url: str | None = None
    published_at: datetime | None = None
    themes: list[ThemeNested] = []
    seo: SeoNested | None = None


class ArticleThemeResponse(BaseModel):
    id: UUID
    slug: str
    title: str
