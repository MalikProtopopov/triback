"""Admin API schemas — protocol history (admission / exclusion)."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.arrears import ArrearUserNested


class ProtocolActionType(StrEnum):
    admission = "admission"
    exclusion = "exclusion"


class AdminUserSnapshot(BaseModel):
    """Staff or any user: email + optional FIO from doctor profile if present."""

    id: UUID
    email: str
    full_name: str | None = None


class ProtocolHistoryCreateRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)
    protocol_title: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(None, max_length=10000)
    doctor_user_id: UUID
    action_type: ProtocolActionType


class ProtocolHistoryUpdateRequest(BaseModel):
    year: int | None = Field(None, ge=2000, le=2100)
    protocol_title: str | None = Field(None, min_length=1, max_length=500)
    notes: str | None = Field(None, max_length=10000)
    doctor_user_id: UUID | None = None
    action_type: ProtocolActionType | None = None


class ProtocolHistoryResponse(BaseModel):
    id: UUID
    year: int
    protocol_title: str
    notes: str | None
    doctor_user_id: UUID
    action_type: str
    created_by_user_id: UUID
    last_edited_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    doctor: ArrearUserNested
    created_by_user: AdminUserSnapshot
    last_edited_by_user: AdminUserSnapshot | None = None


class ProtocolHistoryListResponse(BaseModel):
    data: list[ProtocolHistoryResponse]
    total: int
    limit: int
    offset: int
