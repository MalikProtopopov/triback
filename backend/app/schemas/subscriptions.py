"""Pydantic schemas for subscription and payment initiation endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PayRequest(BaseModel):
    plan_id: UUID
    idempotency_key: str


class PayResponse(BaseModel):
    payment_id: UUID
    payment_url: str
    amount: float
    expires_at: datetime | None = None


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
