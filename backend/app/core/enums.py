"""Application-level string enum constants.

Use these instead of magic strings throughout services and routers.
They mirror the PostgreSQL native enums defined in ``models.base``.
"""

from enum import StrEnum


class DoctorStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


class ChangeStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING_PAYMENT = "pending_payment"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"


class ArticleStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EventStatus(StrEnum):
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class EventRegistrationStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class RecordingStatus(StrEnum):
    HIDDEN = "hidden"
    PUBLISHED = "published"


class VotingSessionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ReceiptStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ModerationAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ProductType(StrEnum):
    ENTRY_FEE = "entry_fee"
    SUBSCRIPTION = "subscription"
    EVENT = "event"


class PaymentProviderEnum(StrEnum):
    YOOKASSA = "yookassa"
    PSB = "psb"
    MANUAL = "manual"
    MONETA = "moneta"


class PlanType(StrEnum):
    ENTRY_FEE = "entry_fee"
    SUBSCRIPTION = "subscription"
