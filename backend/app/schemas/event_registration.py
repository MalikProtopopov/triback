"""Pydantic schemas for event registration and payment."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterForEventRequest(BaseModel):
    tariff_id: UUID
    idempotency_key: str = Field(max_length=255)
    guest_full_name: str | None = Field(None, max_length=300)
    guest_email: EmailStr | None = None
    guest_workplace: str | None = Field(None, max_length=255)
    guest_specialization: str | None = Field(None, max_length=255)
    fiscal_email: EmailStr | None = None


class RegisterForEventResponse(BaseModel):
    registration_id: UUID | None = None
    payment_url: str | None = None
    applied_price: float | None = None
    is_member_price: bool | None = None
    action: str | None = None
    masked_email: str | None = None

    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "summary": "Сценарий 1 — авторизованный пользователь",
                "value": {
                    "registration_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "payment_url": "https://yookassa.ru/payments/...",
                    "applied_price": 5000.0,
                    "is_member_price": True,
                    "action": None,
                    "masked_email": None,
                },
            },
            {
                "summary": "Сценарий 2 — гость с существующим аккаунтом",
                "value": {
                    "registration_id": None,
                    "payment_url": None,
                    "applied_price": None,
                    "is_member_price": None,
                    "action": "login_required",
                    "masked_email": "m***@mail.ru",
                },
            },
            {
                "summary": "Сценарий 3 — новый гость (верификация)",
                "value": {
                    "registration_id": None,
                    "payment_url": None,
                    "applied_price": None,
                    "is_member_price": None,
                    "action": "verification_required",
                    "masked_email": None,
                },
            },
        ]
    })


class ConfirmGuestRegistrationRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    tariff_id: UUID
    idempotency_key: str = Field(max_length=255)
    guest_full_name: str | None = Field(None, max_length=300)
    guest_workplace: str | None = Field(None, max_length=255)
    guest_specialization: str | None = Field(None, max_length=255)
    fiscal_email: EmailStr | None = None


class MyEventListItem(BaseModel):
    registration_id: UUID
    event_id: UUID
    title: str
    event_date: datetime
    status: str
    applied_price: float
    is_member_price: bool


class MyEventsPaginatedResponse(BaseModel):
    data: list[MyEventListItem]
    total: int
    limit: int
    offset: int
