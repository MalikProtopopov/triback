"""Media library assets — S3 object keys tracked for admin picker."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class MediaAsset(Base, UUIDMixin):
    """Uploaded file registered for reuse (e.g. content block gallery keys)."""

    __tablename__ = "media_assets"
    __table_args__ = (Index("idx_media_assets_created_at", "created_at"),)

    s3_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    uploaded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
