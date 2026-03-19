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
    status_label: str = ""
    description: str | None = None
    payment_url: str | None = None
    expires_at: datetime | None = None
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


# ── Admin refund ──────────────────────────────────────────────────

class RefundRequest(BaseModel):
    amount: float | None = Field(None, gt=0, description="Сумма возврата (если None — полный возврат)")
    reason: str = Field(max_length=500, description="Причина возврата")

    model_config = {"json_schema_extra": {
        "example": {"amount": 5000.0, "reason": "Клиент запросил возврат"}
    }}


class RefundResponse(BaseModel):
    refund_id: str
    payment_id: str
    status: str
    amount: float

    model_config = {"json_schema_extra": {
        "example": {
            "refund_id": "2da5c87d-000f-5000-9000-1f2e3d4c5b6a",
            "payment_id": "2da5c87d-000f-5000-8000-1a2b3c4d5e6f",
            "status": "pending",
            "amount": 5000.0,
        }
    }}


# ── Webhook ───────────────────────────────────────────────────────

class WebhookPayload(BaseModel):
    type: str
    event: str
    object: dict[str, Any]
