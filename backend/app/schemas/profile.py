"""Pydantic schemas for doctor profile endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.shared import CityNested


class DocumentNested(BaseModel):
    id: UUID
    document_type: str
    original_filename: str
    uploaded_at: datetime


class PersonalProfileResponse(BaseModel):
    first_name: str
    last_name: str
    middle_name: str | None = None
    phone: str
    passport_data: str | None = None
    registration_address: str | None = None
    city: CityNested | None = None
    clinic_name: str | None = None
    position: str | None = None
    academic_degree: str | None = None
    specialization: str | None = None
    diploma_photo_url: str | None = None
    colleague_contacts: str | None = None
    documents: list[DocumentNested] = []


class PersonalProfileUpdate(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    middle_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    passport_data: str | None = None
    registration_address: str | None = None
    colleague_contacts: str | None = None
    specialization: str | None = Field(None, max_length=255)


class PendingDraftNested(BaseModel):
    status: str
    changes: dict[str, Any]
    submitted_at: datetime
    rejection_reason: str | None = None
    reviewed_at: datetime | None = None


class PublicProfileResponse(BaseModel):
    bio: str | None = None
    public_email: str | None = None
    public_phone: str | None = None
    photo_url: str | None = None
    city: CityNested | None = None
    clinic_name: str | None = None
    academic_degree: str | None = None
    specialization: str | None = None
    pending_draft: PendingDraftNested | None = None


class PublicProfileUpdate(BaseModel):
    bio: str | None = None
    public_email: EmailStr | None = None
    public_phone: str | None = Field(None, max_length=20)
    city_id: UUID | None = None
    clinic_name: str | None = Field(None, max_length=255)
    academic_degree: str | None = Field(None, max_length=255)
    specialization: str | None = Field(None, max_length=255)
    moderation_comment: str | None = None


class PhotoUploadResponse(BaseModel):
    photo_url: str
    message: str
    pending_moderation: bool = False


class DiplomaPhotoResponse(BaseModel):
    diploma_photo_url: str
    message: str
