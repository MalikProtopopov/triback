"""Protocol history entries (admission / exclusion decisions per doctor)."""

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ProtocolHistoryEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "protocol_history_entries"
    __table_args__ = (
        CheckConstraint("year >= 2000 AND year <= 2100", name="chk_protocol_history_year"),
        CheckConstraint(
            "action_type IN ('admission', 'exclusion')",
            name="chk_protocol_history_action_type",
        ),
        Index("idx_protocol_history_doctor_user_id", "doctor_user_id"),
        Index("idx_protocol_history_action_type", "action_type"),
        Index("idx_protocol_history_created_at", "created_at"),
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol_title: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    doctor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    last_edited_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
