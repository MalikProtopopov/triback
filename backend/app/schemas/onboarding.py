"""Pydantic schemas for onboarding endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChooseRoleRequest(BaseModel):
    role: Literal["doctor", "user"]


class OnboardingProfileUpdate(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    middle_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    passport_data: str | None = None
    city_id: UUID | None = None
    clinic_name: str | None = Field(None, max_length=255)
    position: str | None = Field(None, max_length=255)
    academic_degree: str | None = Field(None, max_length=255)


class OnboardingStatusResponse(BaseModel):
    email_verified: bool
    role_chosen: bool
    role: str | None = None
    profile_filled: bool = False
    documents_uploaded: bool = False
    has_medical_diploma: bool = False
    moderation_status: str | None = None
    submitted_at: datetime | None = None
    rejection_comment: str | None = None
    next_step: str


class OnboardingStepResponse(BaseModel):
    message: str
    next_step: str
    profile_id: UUID | None = None
    moderation_status: str | None = None


class DocumentUploadResponse(BaseModel):
    id: UUID
    document_type: str
    original_filename: str
    uploaded_at: datetime
