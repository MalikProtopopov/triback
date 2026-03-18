"""Pydantic schemas for admin event management endpoints."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.shared import ContentBlockNested

# ── Request schemas ───────────────────────────────────────────────

class EventCreateRequest(BaseModel):
    title: str = Field(max_length=500)
    slug: str | None = Field(None, max_length=500)
    description: str | None = None
    event_date: datetime
    event_end_date: datetime | None = None
    location: str | None = Field(None, max_length=500)
    status: Literal["upcoming", "ongoing", "finished", "cancelled"] = "upcoming"


class EventUpdateRequest(BaseModel):
    title: str | None = Field(None, max_length=500)
    slug: str | None = Field(None, max_length=500)
    description: str | None = None
    event_date: datetime | None = None
    event_end_date: datetime | None = None
    location: str | None = Field(None, max_length=500)
    status: Literal["upcoming", "ongoing", "finished", "cancelled"] | None = None


class TariffCreateRequest(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = None
    conditions: str | None = None
    details: str | None = None
    price: float = Field(ge=0)
    member_price: float = Field(ge=0)
    benefits: list[str] = []
    seats_limit: int | None = Field(None, gt=0)
    sort_order: int = 0


class TariffUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    conditions: str | None = None
    details: str | None = None
    price: float | None = Field(None, ge=0)
    member_price: float | None = Field(None, ge=0)
    benefits: list[str] | None = None
    seats_limit: int | None = Field(None, gt=0)
    is_active: bool | None = None
    sort_order: int | None = None


class GalleryCreateRequest(BaseModel):
    title: str = Field(max_length=255)
    access_level: Literal["public", "members_only"] = "public"


class RecordingCreateRequest(BaseModel):
    title: str = Field(max_length=500)
    video_source: Literal["external", "uploaded"]
    video_url: str | None = None
    duration_seconds: int | None = None
    access_level: Literal["public", "members_only", "participants_only"]
    status: Literal["hidden", "published"] = "hidden"

    @model_validator(mode="after")
    def url_required_for_external(self) -> "RecordingCreateRequest":
        if self.video_source == "external" and not self.video_url:
            raise ValueError("video_url is required when video_source is 'external'")
        return self


class RecordingUpdateRequest(BaseModel):
    title: str | None = Field(None, max_length=500)
    video_source: Literal["external", "uploaded"] | None = None
    video_url: str | None = None
    duration_seconds: int | None = None
    access_level: Literal["public", "members_only", "participants_only"] | None = None
    status: Literal["hidden", "published"] | None = None


# ── Response schemas ──────────────────────────────────────────────

class EventCreatedResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    status: str
    created_at: datetime


class EventListItem(BaseModel):
    id: UUID
    title: str
    slug: str
    event_date: datetime
    event_end_date: datetime | None = None
    location: str | None = None
    status: str
    registrations_count: int = 0
    revenue: float = 0.0
    cover_image_url: str | None = None


class TariffNested(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    conditions: str | None = None
    details: str | None = None
    price: float
    member_price: float
    benefits: list[Any] | None = None
    seats_limit: int | None = None
    seats_taken: int = 0
    is_active: bool = True
    sort_order: int = 0


class GalleryNested(BaseModel):
    id: UUID
    title: str
    access_level: str
    photos_count: int = 0
    created_at: datetime


class RecordingNested(BaseModel):
    id: UUID
    title: str
    video_source: str
    video_url: str | None = None
    video_playback_url: str | None = None
    video_file_size: int | None = None
    video_mime_type: str | None = None
    duration_seconds: int | None = None
    access_level: str
    status: str
    sort_order: int = 0
    created_at: datetime


class EventDetailResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str | None = None
    event_date: datetime
    event_end_date: datetime | None = None
    location: str | None = None
    cover_image_url: str | None = None
    status: str
    created_by: UUID
    created_at: datetime
    tariffs: list[TariffNested] = []
    galleries: list[GalleryNested] = []
    recordings: list[RecordingNested] = []
    content_blocks: list[ContentBlockNested] = []


class TariffResponse(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    description: str | None = None
    conditions: str | None = None
    details: str | None = None
    price: float
    member_price: float
    benefits: list[Any] | None = None
    seats_limit: int | None = None
    seats_taken: int = 0
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime


class GalleryResponse(BaseModel):
    id: UUID
    event_id: UUID
    title: str
    access_level: str
    created_at: datetime


class PhotoNested(BaseModel):
    id: UUID
    file_url: str
    thumbnail_url: str | None = None


class PhotoUploadResponse(BaseModel):
    uploaded: int
    photos: list[PhotoNested] = []


class RecordingResponse(BaseModel):
    id: UUID
    event_id: UUID
    title: str
    video_source: str
    video_url: str | None = None
    video_playback_url: str | None = None
    video_file_size: int | None = None
    video_mime_type: str | None = None
    duration_seconds: int | None = None
    access_level: str
    status: str
    sort_order: int = 0
    created_at: datetime


# ── Registration schemas ──────────────────────────────────────────

class RegistrationUserNested(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None


class RegistrationTariffNested(BaseModel):
    id: UUID
    name: str


class RegistrationListItem(BaseModel):
    id: UUID
    user: RegistrationUserNested
    tariff: RegistrationTariffNested
    applied_price: float
    is_member_price: bool
    status: str
    created_at: datetime


class RegistrationSummary(BaseModel):
    total_registrations: int = 0
    confirmed: int = 0
    pending: int = 0
    cancelled: int = 0
    total_revenue: float = 0.0


class RegistrationListResponse(BaseModel):
    data: list[RegistrationListItem]
    summary: RegistrationSummary
    total: int
    limit: int
    offset: int
