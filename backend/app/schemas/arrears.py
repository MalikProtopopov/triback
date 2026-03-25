"""Schemas for membership arrears admin API."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ArrearCreateRequest(BaseModel):
    user_id: UUID
    year: int = Field(ge=2000, le=2100)
    amount: float = Field(gt=0)
    description: str = Field(min_length=1, max_length=2000)
    admin_note: str | None = Field(None, max_length=2000)
    source: Literal["manual", "automatic"] = "manual"


class ArrearUpdateRequest(BaseModel):
    amount: float | None = Field(None, gt=0)
    description: str | None = Field(None, min_length=1, max_length=2000)
    admin_note: str | None = None


class ArrearUserNested(BaseModel):
    """User snapshot for admin arrears list/detail (ФИО из профиля врача, если есть)."""

    id: UUID
    email: str
    full_name: str | None = None
    phone: str | None = None
    telegram_username: str | None = None


class ArrearResponse(BaseModel):
    id: UUID
    user_id: UUID
    year: int
    amount: float
    description: str
    admin_note: str | None
    status: str
    source: str
    escalation_level: str | None
    created_by: UUID | None
    payment_id: UUID | None
    paid_at: datetime | None
    waived_at: datetime | None
    waived_by: UUID | None
    waive_reason: str | None
    created_at: datetime
    updated_at: datetime
    user: ArrearUserNested | None = None


class ArrearListResponse(BaseModel):
    data: list[ArrearResponse]
    total: int
    limit: int
    offset: int


class ArrearSummaryResponse(BaseModel):
    total_open_amount: float
    count_open: int
    total_paid_amount: float
    count_paid: int
    total_waived_amount: float
    count_waived: int


class ArrearWaiveRequest(BaseModel):
    waive_reason: str | None = Field(None, max_length=2000)


class ArrearMarkPaidRequest(BaseModel):
    """Optional link to manual payment row if created separately."""

    note: str | None = Field(None, max_length=500)
