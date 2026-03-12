"""Pydantic schemas for event registration and payment."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterForEventRequest(BaseModel):
    tariff_id: UUID
    idempotency_key: str = Field(max_length=255)
    guest_full_name: str | None = Field(None, max_length=300)
    guest_email: EmailStr | None = None
    guest_workplace: str | None = Field(None, max_length=255)
    guest_specialization: str | None = Field(None, max_length=255)
    fiscal_email: EmailStr | None = None


class RegisterForEventResponse(BaseModel):
    registration_id: UUID
    payment_url: str | None = None
    applied_price: float
    is_member_price: bool


class MyEventListItem(BaseModel):
    registration_id: UUID
    event_id: UUID
    title: str
    event_date: datetime
    status: str
    applied_price: float
    is_member_price: bool
