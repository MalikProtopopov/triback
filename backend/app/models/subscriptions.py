"""Subscription and payment models: plans, subscriptions, payments, receipts."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    PaymentProvider,
    PaymentStatus,
    ProductType,
    ReceiptStatus,
    ReceiptType,
    SubscriptionStatus,
    TimestampMixin,
    UUIDMixin,
)


class Plan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("price > 0", name="chk_plans_price"),
        CheckConstraint("duration_months >= 0", name="chk_plans_duration"),
        Index("idx_plans_active", "is_active"),
        Index("idx_plans_plan_type", "plan_type"),
    )

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    duration_months: Mapped[int] = mapped_column(Integer, server_default="12", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    plan_type: Mapped[str] = mapped_column(
        String(20), server_default="subscription", nullable=False
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at",
            name="chk_subs_dates",
        ),
        Index("idx_subs_user_status", "user_id", "status"),
        Index("idx_subs_ends_at", "ends_at"),
        Index("idx_subs_status", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        SubscriptionStatus, server_default="pending_payment", nullable=False
    )
    is_first_year: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")
    payments: Mapped[list["Payment"]] = relationship(back_populates="subscription")


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_payments_amount_positive"),
        Index("idx_payments_user_created", "user_id", "created_at"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_product_type", "product_type"),
        Index("idx_payments_provider", "payment_provider"),
        Index(
            "uix_payments_external_id",
            "external_payment_id",
            unique=True,
            postgresql_where="external_payment_id IS NOT NULL",
        ),
        Index(
            "uix_payments_idempotency",
            "idempotency_key",
            unique=True,
            postgresql_where="idempotency_key IS NOT NULL",
        ),
        Index("idx_payments_subscription", "subscription_id"),
        Index("idx_payments_event_reg", "event_registration_id"),
        Index("idx_payments_arrear_id", "arrear_id"),
        Index("idx_payments_created_at", "created_at"),
        Index(
            "idx_payments_moneta_op",
            "moneta_operation_id",
            postgresql_where="moneta_operation_id IS NOT NULL",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    product_type: Mapped[str] = mapped_column(ProductType, nullable=False)
    payment_provider: Mapped[str] = mapped_column(
        PaymentProvider, server_default="yookassa", nullable=False
    )
    status: Mapped[str] = mapped_column(
        PaymentStatus, server_default="pending", nullable=False
    )
    subscription_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    event_registration_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("event_registrations.id", ondelete="SET NULL")
    )
    arrear_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("membership_arrears.id", ondelete="SET NULL")
    )
    external_payment_id: Mapped[str | None] = mapped_column(String(255))
    external_payment_url: Mapped[str | None] = mapped_column(String(1000))
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(500))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moneta_operation_id: Mapped[str | None] = mapped_column(String(255))

    subscription: Mapped["Subscription | None"] = relationship(back_populates="payments")
    receipts: Mapped[list["Receipt"]] = relationship(back_populates="payment")


class Receipt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "receipts"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_receipts_amount_positive"),
        UniqueConstraint("payment_id", "receipt_type", name="uix_receipts_payment_type"),
        Index("idx_receipts_status", "status"),
        Index("idx_receipts_payment", "payment_id"),
    )

    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False
    )
    receipt_type: Mapped[str] = mapped_column(
        ReceiptType, server_default="payment", nullable=False
    )
    provider_receipt_id: Mapped[str | None] = mapped_column(String(255))
    fiscal_number: Mapped[str | None] = mapped_column(String(100))
    fiscal_document: Mapped[str | None] = mapped_column(String(100))
    fiscal_sign: Mapped[str | None] = mapped_column(String(100))
    receipt_url: Mapped[str | None] = mapped_column(String(1000))
    receipt_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        ReceiptStatus, server_default="pending", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    payment: Mapped["Payment"] = relationship(back_populates="receipts")
