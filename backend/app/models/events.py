"""Event models: events, event_tariffs, event_registrations,
event_galleries, event_gallery_photos, event_recordings."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    AccessLevel,
    Base,
    EventRegistrationStatus,
    EventStatus,
    RecordingStatus,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VideoSource,
)


class Event(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_status_date", "status", "event_date"),
        Index("idx_events_date", "event_date"),
        Index("idx_events_created_by", "created_by"),
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(500))
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        EventStatus, server_default="upcoming", nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    tariffs: Mapped[list["EventTariff"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    registrations: Mapped[list["EventRegistration"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    galleries: Mapped[list["EventGallery"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    recordings: Mapped[list["EventRecording"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class EventTariff(Base, UUIDMixin):
    __tablename__ = "event_tariffs"
    __table_args__ = (
        CheckConstraint("price >= 0", name="chk_tariffs_price"),
        CheckConstraint("member_price >= 0", name="chk_tariffs_member_price"),
        CheckConstraint(
            "seats_limit IS NULL OR seats_limit > 0", name="chk_tariffs_seats_limit"
        ),
        CheckConstraint("seats_taken >= 0", name="chk_tariffs_seats_taken"),
        Index("idx_tariffs_event_active", "event_id", "is_active"),
    )

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[str | None] = mapped_column(Text)
    details: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    member_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    benefits: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    seats_limit: Mapped[int | None] = mapped_column(Integer)
    seats_taken: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="tariffs")
    registrations: Mapped[list["EventRegistration"]] = relationship(
        back_populates="tariff"
    )


class EventRegistration(Base, UUIDMixin):
    __tablename__ = "event_registrations"
    __table_args__ = (
        CheckConstraint("applied_price >= 0", name="chk_reg_price"),
        UniqueConstraint(
            "user_id", "event_id", "event_tariff_id",
            name="uix_event_reg_user_event_tariff",
        ),
        Index("idx_event_reg_event", "event_id"),
        Index("idx_event_reg_tariff", "event_tariff_id"),
        Index("idx_event_reg_status", "status"),
        Index("idx_event_reg_event_status", "event_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    event_tariff_id: Mapped[UUID] = mapped_column(
        ForeignKey("event_tariffs.id", ondelete="RESTRICT"), nullable=False
    )
    applied_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    is_member_price: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    status: Mapped[str] = mapped_column(
        EventRegistrationStatus, server_default="pending", nullable=False
    )
    guest_full_name: Mapped[str | None] = mapped_column(String(300))
    guest_email: Mapped[str | None] = mapped_column(String(255))
    guest_workplace: Mapped[str | None] = mapped_column(String(255))
    guest_specialization: Mapped[str | None] = mapped_column(String(255))
    fiscal_email: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="registrations")
    tariff: Mapped["EventTariff"] = relationship(back_populates="registrations")


class EventGallery(Base, UUIDMixin):
    __tablename__ = "event_galleries"
    __table_args__ = (
        Index("idx_galleries_event_access", "event_id", "access_level"),
    )

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    access_level: Mapped[str] = mapped_column(
        AccessLevel, server_default="public", nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="galleries")
    photos: Mapped[list["EventGalleryPhoto"]] = relationship(
        back_populates="gallery", cascade="all, delete-orphan"
    )


class EventGalleryPhoto(Base, UUIDMixin):
    __tablename__ = "event_gallery_photos"
    __table_args__ = (
        Index("idx_gallery_photos_sort", "gallery_id", "sort_order"),
    )

    gallery_id: Mapped[UUID] = mapped_column(
        ForeignKey("event_galleries.id", ondelete="CASCADE"), nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    gallery: Mapped["EventGallery"] = relationship(back_populates="photos")


class EventRecording(Base, UUIDMixin):
    __tablename__ = "event_recordings"
    __table_args__ = (
        CheckConstraint(
            "(video_source = 'external' AND video_url IS NOT NULL) "
            "OR (video_source = 'uploaded' AND video_file_key IS NOT NULL)",
            name="chk_recording_source",
        ),
        Index("idx_recordings_event_status", "event_id", "status"),
    )

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    video_source: Mapped[str] = mapped_column(VideoSource, nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(1000))
    video_file_key: Mapped[str | None] = mapped_column(String(500))
    video_file_size: Mapped[int | None] = mapped_column(BigInteger)
    video_mime_type: Mapped[str | None] = mapped_column(String(100))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    access_level: Mapped[str] = mapped_column(
        AccessLevel, server_default="participants_only", nullable=False
    )
    status: Mapped[str] = mapped_column(
        RecordingStatus, server_default="hidden", nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="recordings")
