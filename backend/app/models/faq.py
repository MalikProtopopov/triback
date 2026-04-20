"""FAQ model: expert Q&A entries from the old trichologia site."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class FaqEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "faq_entries"
    __table_args__ = (
        Index("idx_faq_entries_is_active", "is_active"),
        Index("idx_faq_entries_created_at", "created_at"),
    )

    question_title: Mapped[str] = mapped_column(String(500), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    original_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
