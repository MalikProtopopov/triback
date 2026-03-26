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
    access_token: str | None = None
    refresh_token: str | None = None

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
                    "access_token": None,
                    "refresh_token": None,
                },
            },
            {
                "summary": "Сценарий 2 — гость с существующим аккаунтом (OTP отправлен)",
                "value": {
                    "registration_id": None,
                    "payment_url": None,
                    "applied_price": None,
                    "is_member_price": None,
                    "action": "verify_existing",
                    "masked_email": "m***@mail.ru",
                    "access_token": None,
                    "refresh_token": None,
                },
            },
            {
                "summary": "Сценарий 3 — новый гость (OTP отправлен)",
                "value": {
                    "registration_id": None,
                    "payment_url": None,
                    "applied_price": None,
                    "is_member_price": None,
                    "action": "verify_new_email",
                    "masked_email": "n***@example.com",
                    "access_token": None,
                    "refresh_token": None,
                },
            },
            {
                "summary": "Сценарий 4 — после подтверждения кода (confirm-guest-registration)",
                "value": {
                    "registration_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "payment_url": "https://payanyway.ru/assistant.htm?operationId=...",
                    "applied_price": 7000.0,
                    "is_member_price": False,
                    "action": None,
                    "masked_email": None,
                    "access_token": "eyJhbGciOiJSUzI1NiIs...",
                    "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
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
    event_slug: str
    title: str
    event_date: datetime
    status: str
    applied_price: float
    is_member_price: bool
    tariff_name: str | None = None


class MyEventsPaginatedResponse(BaseModel):
    data: list[MyEventListItem]
    total: int
    limit: int
    offset: int


# ── User event registrations list (LK + admin) ────────────────────


class UserEventRegistrationNested(BaseModel):
    """Регистрация на мероприятие."""

    id: UUID
    status: str
    created_at: datetime
    guest_full_name: str | None = None
    guest_email: str | None = None
    guest_workplace: str | None = None
    guest_specialization: str | None = None
    fiscal_email: str | None = None


class UserEventNested(BaseModel):
    id: UUID
    slug: str
    title: str
    event_date: datetime
    event_end_date: datetime | None = None
    location: str | None = None
    status: str
    cover_image_url: str | None = None


class UserEventTariffNested(BaseModel):
    id: UUID
    name: str
    price: float
    member_price: float
    applied_price: float
    is_member_price: bool


class UserEventRegistrationPaymentNested(BaseModel):
    id: UUID
    amount: float
    product_type: str
    status: str
    status_label: str = ""
    description: str | None = None
    payment_url: str | None = None
    paid_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    external_payment_id: str | None = None


class UserEventRegistrationListItem(BaseModel):
    registration: UserEventRegistrationNested
    event: UserEventNested
    tariff: UserEventTariffNested
    payment: UserEventRegistrationPaymentNested | None = None


class UserEventRegistrationsPaginatedResponse(BaseModel):
    data: list[UserEventRegistrationListItem]
    total: int
    limit: int
    offset: int
