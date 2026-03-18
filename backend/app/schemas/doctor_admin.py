"""Pydantic schemas for admin doctor management endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.shared import (
    CityNested,
    ContentBlockNested,
    PaymentNested,
    SubscriptionNested,
)

# ── Nested helpers ────────────────────────────────────────────────


class SpecializationNested(BaseModel):
    id: UUID
    name: str


class DocumentNested(BaseModel):
    id: UUID
    document_type: str
    original_filename: str
    file_url: str | None = None
    file_size: int
    mime_type: str
    uploaded_at: datetime


class PendingDraftNested(BaseModel):
    id: UUID
    changes: dict
    changed_fields: list[str]
    status: str
    moderation_comment: str | None = None
    submitted_at: datetime
    rejection_reason: str | None = None


class ModerationHistoryNested(BaseModel):
    id: UUID
    admin_email: str | None = None
    action: str
    comment: str | None = None
    created_at: datetime


# ── Admin create doctor ───────────────────────────────────────────

class AdminCreateDoctorRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    middle_name: str | None = Field(None, max_length=100)
    city_id: UUID | None = None
    clinic_name: str | None = Field(None, max_length=255)
    position: str | None = Field(None, max_length=255)
    academic_degree: str | None = Field(None, max_length=255)
    bio: str | None = None
    public_email: str | None = Field(None, max_length=255)
    public_phone: str | None = Field(None, max_length=20)
    specialization_ids: list[UUID] | None = None
    status: Literal["approved", "pending_review"] = "approved"
    send_invite: bool = True

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "doctor@example.com",
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "phone": "+79001234567",
                    "city_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "clinic_name": "Клиника здоровья",
                    "send_invite": True,
                }
            ]
        }
    }


class AdminCreateDoctorResponse(BaseModel):
    user_id: UUID
    profile_id: UUID
    email: str
    first_name: str
    last_name: str
    status: str
    temp_password: str | None = None


# ── Doctor list ───────────────────────────────────────────────────

class DoctorListItemResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    phone: str
    city: CityNested | None = None
    specialization: str | None = None
    moderation_status: str
    has_medical_diploma: bool
    subscription: SubscriptionNested | None = None
    has_pending_changes: bool = False
    has_photo_in_draft: bool = False
    created_at: datetime


# ── Doctor detail ─────────────────────────────────────────────────

class DoctorDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    phone: str
    passport_data: str | None = None
    city: CityNested | None = None
    clinic_name: str | None = None
    position: str | None = None
    specialization: str | None = None
    academic_degree: str | None = None
    bio: str | None = None
    public_email: str | None = None
    public_phone: str | None = None
    photo_url: str | None = None
    moderation_status: str
    has_medical_diploma: bool
    diploma_photo_url: str | None = None
    slug: str | None = None
    documents: list[DocumentNested] = []
    subscription: SubscriptionNested | None = None
    payments: list[PaymentNested] = []
    pending_draft: PendingDraftNested | None = None
    moderation_history: list[ModerationHistoryNested] = []
    content_blocks: list[ContentBlockNested] = []
    created_at: datetime


# ── Moderation actions ────────────────────────────────────────────

class ModerateRequest(BaseModel):
    action: Literal["approve", "reject"]
    comment: str | None = None

    @model_validator(mode="after")
    def comment_required_on_reject(self) -> "ModerateRequest":
        if self.action == "reject" and not self.comment:
            raise ValueError("Comment is required when rejecting")
        return self


class ModerateResponse(BaseModel):
    moderation_status: str
    message: str


class ApproveDraftRequest(BaseModel):
    action: Literal["approve", "reject"]
    rejection_reason: str | None = None

    @model_validator(mode="after")
    def reason_required_on_reject(self) -> "ApproveDraftRequest":
        if self.action == "reject" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when rejecting")
        return self


# ── Toggle active ─────────────────────────────────────────────────

class ToggleActiveRequest(BaseModel):
    is_public: bool


class ToggleActiveResponse(BaseModel):
    is_public: bool
    message: str


# ── Send reminder / email ────────────────────────────────────────

class SendReminderRequest(BaseModel):
    message: str | None = None


class SendEmailRequest(BaseModel):
    subject: str = Field(max_length=255)
    body: str


# ── Import ────────────────────────────────────────────────────────

class ImportStartResponse(BaseModel):
    task_id: str
    message: str


class ImportErrorItem(BaseModel):
    row: int
    error: str


class ImportStatusResponse(BaseModel):
    status: str
    total_rows: int = 0
    imported: int = 0
    errors: list[ImportErrorItem] = []


# ── Portal users ──────────────────────────────────────────────────

class PortalUserListItem(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: str | None = None
    role_display: str | None = None
    onboarding_status: str | None = None
    doctor_profile_id: UUID | None = None
    subscription: SubscriptionNested | None = None
    last_payment: PaymentNested | None = None
    created_at: datetime


class PortalUserDetailResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: str | None = None
    role_display: str | None = None
    is_verified: bool = False
    onboarding_status: str | None = None
    doctor_profile_id: UUID | None = None
    doctor_profile_status: str | None = None
    subscription: SubscriptionNested | None = None
    payments: list[PaymentNested] = []
    created_at: datetime
