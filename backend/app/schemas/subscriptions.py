"""Pydantic schemas for subscription and payment initiation endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PayRequest(BaseModel):
    plan_id: UUID
    idempotency_key: str


class PayResponse(BaseModel):
    payment_id: UUID
    payment_url: str
    amount: float
    expires_at: datetime | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "payment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "payment_url": "https://yookassa.ru/payments/...",
            "amount": 15000.0,
            "expires_at": "2026-04-01T12:00:00Z",
        }
    })


class PlanNested(BaseModel):
    code: str
    name: str


class CurrentSubscriptionNested(BaseModel):
    id: UUID
    plan: PlanNested
    status: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    days_remaining: int | None = None


class UserPaymentListItem(BaseModel):
    id: UUID
    amount: float
    product_type: str
    status: str
    description: str | None = None
    paid_at: datetime | None = None
    created_at: datetime


class ReceiptResponse(BaseModel):
    id: UUID
    receipt_type: str
    provider_receipt_id: str | None = None
    receipt_url: str | None = None
    fiscal_number: str | None = None
    fiscal_document: str | None = None
    fiscal_sign: str | None = None
    amount: float
    status: str


class SubscriptionStatusResponse(BaseModel):
    has_subscription: bool
    current_subscription: CurrentSubscriptionNested | None = None
    has_paid_entry_fee: bool
    can_renew: bool
    next_action: str | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "has_subscription": True,
            "current_subscription": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "plan": {"code": "annual", "name": "Годовой взнос"},
                "status": "active",
                "starts_at": "2026-01-01T00:00:00Z",
                "ends_at": "2027-01-01T00:00:00Z",
                "days_remaining": 295,
            },
            "has_paid_entry_fee": True,
            "can_renew": False,
            "next_action": None,
        }
    })


class UserPaymentPaginatedResponse(BaseModel):
    data: list[UserPaymentListItem]
    total: int
    limit: int
    offset: int
