"""Inbox table for raw payment webhook persistence and processing state."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PaymentWebhookInbox(Base, TimestampMixin):
    """Persists every incoming payment webhook before processing.

    Status lifecycle:
      received  → verified → processing → done
                ↘ dead (bad signature / max retries exceeded)
                           ↘ error     (transient failure, will retry)

    ``external_event_key`` is a stable, provider-scoped dedup key, e.g.:
      ``yookassa:payment.succeeded:pay_xxxxx``
      ``moneta_pay:op-12345``
    The unique index on ``(provider, external_event_key)`` provides a
    DB-level guard against duplicate rows independent of Redis.
    """

    __tablename__ = "payment_webhook_inbox"
    __table_args__ = (
        Index("ix_pwi_provider_ext", "provider", "external_event_key", unique=True),
        Index("ix_pwi_status_next_run", "status", "next_run_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Provider slug: yookassa | moneta_pay | moneta_receipt
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    # Stable dedup key scoped to the provider, e.g. "yookassa:payment.succeeded:pay_xxx"
    external_event_key: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_headers: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Parsed JSON body (or None for form-encoded webhooks stored as text elsewhere)
    raw_body: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(64))
    # received | verified | processing | done | error | dead
    status: Mapped[str] = mapped_column(String(32), default="received", nullable=False)
    verify_error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
