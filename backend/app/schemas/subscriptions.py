"""Pydantic schemas for subscription and payment initiation endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PayRequest(BaseModel):
    plan_id: UUID
    idempotency_key: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "plan_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
        }
    })


class PayResponse(BaseModel):
    payment_id: UUID
    payment_url: str
    amount: float
    expires_at: datetime | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "payment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "payment_url": "https://moneta.ru/assistant.htm?operationId=...",
            "amount": 15000.0,
            "expires_at": "2026-04-01T12:00:00Z",
        }
    })


class PlanNested(BaseModel):
    id: UUID | None = None
    code: str
    name: str
    plan_type: str = "subscription"
    price: float = 0
    duration_months: int = 12


class CurrentSubscriptionNested(BaseModel):
    id: UUID
    plan: PlanNested
    status: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    days_remaining: int | None = None


_STATUS_LABELS: dict[str, str] = {
    "pending": "Ожидает оплаты",
    "succeeded": "Оплачен",
    "failed": "Отклонён",
    "expired": "Истёк",
    "refunded": "Возвращён",
    "partially_refunded": "Частичный возврат",
}


class UserPaymentListItem(BaseModel):
    id: UUID
    amount: float
    product_type: str
    status: str
    status_label: str = ""
    description: str | None = None
    payment_url: str | None = None
    expires_at: datetime | None = None
    paid_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
            "amount": 20000.0,
            "product_type": "entry_fee",
            "status": "succeeded",
            "status_label": "Оплачен",
            "description": "Вступительный взнос + Годовой взнос — Ассоциация трихологов",
            "payment_url": None,
            "expires_at": None,
            "paid_at": "2026-01-15T14:30:00Z",
            "created_at": "2026-01-15T14:25:00Z",
        }
    })


class PaymentStatusResponse(BaseModel):
    """Публичный статус платежа (для страницы /payment/success)."""

    payment_id: UUID
    status: str
    product_type: str
    amount: float
    created_at: datetime
    paid_at: datetime | None = None
    event_id: UUID | None = None
    event_title: str | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "payment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "status": "succeeded",
            "product_type": "event",
            "amount": 5000.0,
            "created_at": "2026-03-20T10:00:00Z",
            "paid_at": "2026-03-20T10:05:00Z",
            "event_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "event_title": "Конференция 2026",
        }
    })


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

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "d4e5f6a7-b8c9-0123-def0-123456789abc",
            "receipt_type": "payment",
            "provider_receipt_id": "12345",
            "receipt_url": "https://receipt.moneta.ru/receipt/12345",
            "fiscal_number": "FN9876543210",
            "fiscal_document": "FD12345",
            "fiscal_sign": "FS987654321",
            "amount": 20000.0,
            "status": "succeeded",
        }
    })


class SubscriptionStatusResponse(BaseModel):
    has_subscription: bool
    current_subscription: CurrentSubscriptionNested | None = None
    has_paid_entry_fee: bool
    can_renew: bool
    next_action: str | None = None
    entry_fee_required: bool = False
    entry_fee_plan: PlanNested | None = None
    available_plans: list[PlanNested] = []

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "has_subscription": True,
            "current_subscription": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "plan": {
                    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "code": "annual",
                    "name": "Годовой взнос",
                    "plan_type": "subscription",
                    "price": 15000.0,
                    "duration_months": 12,
                },
                "status": "active",
                "starts_at": "2026-01-01T00:00:00Z",
                "ends_at": "2027-01-01T00:00:00Z",
                "days_remaining": 295,
            },
            "has_paid_entry_fee": True,
            "can_renew": False,
            "next_action": None,
            "entry_fee_required": False,
            "entry_fee_plan": None,
            "available_plans": [],
        }
    })


class UserPaymentPaginatedResponse(BaseModel):
    data: list[UserPaymentListItem]
    total: int
    limit: int
    offset: int
