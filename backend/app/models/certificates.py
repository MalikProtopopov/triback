"""Certificate model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CertificateType, UUIDMixin


class Certificate(Base, UUIDMixin):
    __tablename__ = "certificates"
    __table_args__ = (
        CheckConstraint("year >= 2020 AND year <= 2100", name="chk_certs_year"),
        Index(
            "uix_certs_member_year",
            "doctor_profile_id",
            "year",
            unique=True,
            postgresql_where="certificate_type = 'member'",
        ),
        Index(
            "uix_certs_event",
            "doctor_profile_id",
            "event_id",
            unique=True,
            postgresql_where="certificate_type = 'event' AND event_id IS NOT NULL",
        ),
        Index("idx_certs_user", "user_id"),
        Index("idx_certs_type", "certificate_type"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    doctor_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    certificate_type: Mapped[str] = mapped_column(
        CertificateType, server_default="member", nullable=False
    )
    year: Mapped[int | None] = mapped_column(SmallInteger)
    event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="SET NULL")
    )
    certificate_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
