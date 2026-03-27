"""Admin media library schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MediaAssetItem(BaseModel):
    id: UUID
    s3_key: str
    public_url: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    width: int | None = None
    height: int | None = None
    created_at: datetime


class MediaAssetListResponse(BaseModel):
    data: list[MediaAssetItem]
    total: int


class MediaUploadResponse(BaseModel):
    id: UUID
    s3_key: str
    public_url: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "01930b4a-0000-7000-8000-000000000001",
                "s3_key": "media-library/abc.jpg",
                "public_url": "https://cdn.example.com/media-library/abc.jpg",
            }
        }
    }

