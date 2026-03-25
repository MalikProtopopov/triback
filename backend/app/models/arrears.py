"""Membership arrears (manual + automatic)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ArrearStatus, Base, TimestampMixin, UUIDMixin


class MembershipArrear(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "membership_arrears"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_membership_arrears_amount_positive"),
        CheckConstraint("year >= 2000 AND year <= 2100", name="chk_membership_arrears_year"),
        Index("idx_membership_arrears_user_id", "user_id"),
        Index("idx_membership_arrears_status", "status"),
        Index("idx_membership_arrears_year", "year"),
        Index(
            "uix_membership_arrears_user_year_open",
            "user_id",
            "year",
            unique=True,
            postgresql_where="status = 'open'",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    admin_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        ArrearStatus, server_default="open", nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), server_default="manual", nullable=False)
    escalation_level: Mapped[str | None] = mapped_column(String(32))
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    # UUID of the payment that closed this row — no ORM-level FK to ``payments`` to avoid a
    # circular dependency with ``payments.arrear_id`` (Alembic may still add a DB constraint).
    payment_id: Mapped[UUID | None] = mapped_column()
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waived_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    waive_reason: Mapped[str | None] = mapped_column(Text)
