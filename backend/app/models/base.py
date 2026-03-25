"""SQLAlchemy declarative base, mixins, and PostgreSQL enum types."""

from datetime import datetime
from uuid import UUID

import uuid_utils
from sqlalchemy import Boolean, DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class UUIDMixin:
    """UUID v7 primary key."""

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=lambda: UUID(str(uuid_utils.uuid7())),
    )


class TimestampMixin:
    """Automatic created_at / updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Soft delete support — mark as deleted instead of removing rows."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


# ---------------------------------------------------------------------------
# PostgreSQL native enum types
# ---------------------------------------------------------------------------

DoctorStatus = SAEnum(
    "pending_review",
    "approved",
    "rejected",
    "active",
    "deactivated",
    name="doctor_status",
    native_enum=True,
)

SubscriptionStatus = SAEnum(
    "active",
    "expired",
    "pending_payment",
    "cancelled",
    name="subscription_status",
    native_enum=True,
)

PaymentStatus = SAEnum(
    "pending",
    "succeeded",
    "failed",
    "expired",
    "partially_refunded",
    "refunded",
    name="payment_status",
    native_enum=True,
)

ProductType = SAEnum(
    "entry_fee",
    "subscription",
    "event",
    "membership_arrears",
    name="product_type",
    native_enum=True,
)

ArrearStatus = SAEnum(
    "open",
    "paid",
    "cancelled",
    "waived",
    name="arrear_status",
    native_enum=True,
)

ChangeStatus = SAEnum(
    "pending",
    "approved",
    "rejected",
    name="change_status",
    native_enum=True,
)

EventStatus = SAEnum(
    "upcoming",
    "ongoing",
    "finished",
    "cancelled",
    name="event_status",
    native_enum=True,
)

DocumentType = SAEnum(
    "medical_diploma",
    "retraining_cert",
    "oncology_cert",
    "additional_cert",
    name="document_type",
    native_enum=True,
)

ModerationAction = SAEnum(
    "approve",
    "reject",
    name="moderation_action",
    native_enum=True,
)

NotificationChannel = SAEnum(
    "email",
    "telegram",
    name="notification_channel",
    native_enum=True,
)

CertificateType = SAEnum(
    "member",
    "event",
    name="certificate_type",
    native_enum=True,
)

ContentBlockType = SAEnum(
    "text",
    "image",
    "video",
    "file",
    name="content_block_type",
    native_enum=True,
)

ArticleStatus = SAEnum(
    "draft",
    "published",
    "archived",
    name="article_status",
    native_enum=True,
)

VotingSessionStatus = SAEnum(
    "draft",
    "active",
    "closed",
    "cancelled",
    name="voting_session_status",
    native_enum=True,
)

UserRole = SAEnum(
    "admin",
    "manager",
    "accountant",
    "doctor",
    "user",
    name="user_role",
    native_enum=True,
)

PaymentProvider = SAEnum(
    "yookassa",
    "psb",
    "manual",
    "moneta",
    name="payment_provider",
    native_enum=True,
)

RecordingStatus = SAEnum(
    "hidden",
    "published",
    name="recording_status",
    native_enum=True,
)

VideoSource = SAEnum(
    "uploaded",
    "external",
    name="video_source",
    native_enum=True,
)

AccessLevel = SAEnum(
    "public",
    "members_only",
    "participants_only",
    name="access_level",
    native_enum=True,
)

NotificationStatus = SAEnum(
    "pending",
    "sent",
    "failed",
    name="notification_status",
    native_enum=True,
)

ReceiptStatus = SAEnum(
    "pending",
    "succeeded",
    "failed",
    name="receipt_status",
    native_enum=True,
)

ReceiptType = SAEnum(
    "payment",
    "refund",
    name="receipt_type",
    native_enum=True,
)

EventRegistrationStatus = SAEnum(
    "pending",
    "confirmed",
    "cancelled",
    name="event_registration_status",
    native_enum=True,
)

BoardRole = SAEnum(
    "pravlenie",
    "president",
    name="board_role",
    native_enum=True,
)
