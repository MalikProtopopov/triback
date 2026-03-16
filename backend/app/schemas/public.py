"""Pydantic schemas for public (guest) API endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ── SEO ───────────────────────────────────────────────────────────

class SeoNested(BaseModel):
    title: str | None = None
    description: str | None = None
    og_url: str | None = None
    og_type: str | None = None
    og_image: str | None = None
    twitter_card: str | None = "summary_large_image"
    canonical_url: str | None = None


# ── Content blocks (shared) ───────────────────────────────────────

class ContentBlockPublicNested(BaseModel):
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
    content_blocks: list[ContentBlockPublicNested] = []


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
    content_blocks: list[ContentBlockPublicNested] = []

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "title": "Конференция трихологов 2026",
            "slug": "conference-2026",
            "description": "Ежегодная конференция...",
            "event_date": "2026-06-15T10:00:00Z",
            "event_end_date": "2026-06-16T18:00:00Z",
            "location": "Москва, Крокус Экспо",
            "cover_image_url": "/media/events/cover-2026.jpg",
            "tariffs": [
                {
                    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "name": "Стандарт",
                    "description": "Участие в основной программе",
                    "conditions": None,
                    "details": None,
                    "price": 10000.0,
                    "member_price": 5000.0,
                    "benefits": ["Доступ к записям", "Сертификат"],
                    "seats_limit": 200,
                    "seats_available": 150,
                }
            ],
            "galleries": [],
            "recordings": [],
            "seo": {
                "title": "Конференция трихологов 2026",
                "description": "Ежегодная конференция...",
                "og_url": None,
                "og_type": "website",
                "og_image": None,
                "twitter_card": "summary_large_image",
                "canonical_url": None,
            },
        }
    })


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
    content_blocks: list[ContentBlockPublicNested] = []


class ArticleThemeResponse(BaseModel):
    id: UUID
    slug: str
    title: str


# ── Wrappers for endpoints that return {"data": [...]} ──────────


class CityListResponse(BaseModel):
    data: list[CityResponse | CityWithDoctorsResponse]


class GalleryPhotoItem(BaseModel):
    id: str
    file_url: str | None = None
    thumbnail_url: str | None = None
    caption: str | None = None


class GalleryItem(BaseModel):
    id: str
    title: str
    access_level: str
    photos: list[GalleryPhotoItem] = []


class GalleryListResponse(BaseModel):
    data: list[GalleryItem]


class RecordingItem(BaseModel):
    id: str
    title: str
    video_source: str
    video_url: str | None = None
    duration_seconds: int | None = None
    access_level: str


class RecordingListResponse(BaseModel):
    data: list[RecordingItem]


class ArticleThemeListResponse(BaseModel):
    data: list[ArticleThemeResponse]


class OrgDocPublicItem(BaseModel):
    id: str
    title: str
    slug: str
    content: str | None = None
    file_url: str | None = None


class OrgDocPublicDetailResponse(BaseModel):
    id: str
    title: str
    slug: str
    content: str | None = None
    file_url: str | None = None
    content_blocks: list[ContentBlockPublicNested] = []


class OrgDocPublicListResponse(BaseModel):
    data: list[OrgDocPublicItem]
