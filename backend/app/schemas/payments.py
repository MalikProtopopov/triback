"""Pydantic schemas for admin payment and webhook endpoints."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ── Admin payment list ────────────────────────────────────────────

class PaymentUserNested(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None


class PaymentListItem(BaseModel):
    id: UUID
    user: PaymentUserNested
    amount: float
    product_type: str
    payment_provider: str
    status: str
    description: str | None = None
    has_receipt: bool = False
    paid_at: datetime | None = None
    created_at: datetime


class PaymentsSummary(BaseModel):
    total_amount: float
    count_completed: int
    count_pending: int


class PaymentListResponse(BaseModel):
    data: list[PaymentListItem]
    summary: PaymentsSummary
    total: int
    limit: int
    offset: int


# ── Manual payment ────────────────────────────────────────────────

class ManualPaymentRequest(BaseModel):
    user_id: UUID
    amount: float = Field(gt=0)
    product_type: Literal["entry_fee", "subscription", "event"]
    description: str
    subscription_id: UUID | None = None
    event_registration_id: UUID | None = None


class ManualPaymentResponse(BaseModel):
    payment_id: UUID
    status: str
    payment_provider: str


# ── Webhook ───────────────────────────────────────────────────────

class WebhookPayload(BaseModel):
    type: str
    event: str
    object: dict[str, Any]
