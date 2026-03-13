"""Pydantic schemas for content blocks CRUD."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

ENTITY_TYPE = Literal["article", "event", "doctor_profile", "organization_document"]
BLOCK_TYPE = Literal["text", "image", "video", "gallery", "link"]
DEVICE_TYPE = Literal["mobile", "desktop", "both"]


class ContentBlockCreateRequest(BaseModel):
    entity_type: ENTITY_TYPE
    entity_id: UUID
    block_type: BLOCK_TYPE
    locale: str = Field("ru", max_length=5)
    sort_order: int = 0
    title: str | None = Field(None, max_length=255)
    content: str | None = None
    media_url: str | None = Field(None, max_length=500)
    thumbnail_url: str | None = Field(None, max_length=500)
    link_url: str | None = Field(None, max_length=500)
    link_label: str | None = Field(None, max_length=255)
    device_type: DEVICE_TYPE = "both"
    block_metadata: dict[str, Any] | None = None

    model_config = {"json_schema_extra": {
        "example": {
            "entity_type": "article",
            "entity_id": "01930b4a-0000-7000-8000-000000000001",
            "block_type": "text",
            "sort_order": 0,
            "title": "Введение",
            "content": "<p>Текст блока...</p>",
            "device_type": "both",
        }
    }}


class ContentBlockUpdateRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    content: str | None = None
    media_url: str | None = Field(None, max_length=500)
    thumbnail_url: str | None = Field(None, max_length=500)
    link_url: str | None = Field(None, max_length=500)
    link_label: str | None = Field(None, max_length=255)
    device_type: DEVICE_TYPE | None = None
    block_metadata: dict[str, Any] | None = None


class ReorderItem(BaseModel):
    id: UUID
    sort_order: int


class ContentBlockReorderRequest(BaseModel):
    items: list[ReorderItem] = Field(min_length=1)


class ContentBlockResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    locale: str
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
    created_at: datetime
    updated_at: datetime


class ContentBlockListResponse(BaseModel):
    data: list[ContentBlockResponse]
    total: int
