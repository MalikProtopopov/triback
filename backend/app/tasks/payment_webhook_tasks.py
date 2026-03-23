"""Background tasks for reliable payment webhook processing via the inbox table."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment_webhook_inbox import PaymentWebhookInbox
from app.tasks import broker

logger = structlog.get_logger(__name__)

# Exponential backoff caps: attempt 1→1s, 2→2s, 3→4s, 4→8s, 5→16s, 6→32s (cap).
_BACKOFF_BASE_SECONDS = 1
_BACKOFF_CAP_SECONDS = 32
_MAX_ATTEMPTS = 6


def _next_run_at(attempts: int) -> datetime:
    delay = min(_BACKOFF_BASE_SECONDS * (2 ** (attempts - 1)), _BACKOFF_CAP_SECONDS)
    return datetime.now(UTC) + timedelta(seconds=delay)


@broker.task(retry_on_error=False)
async def process_payment_webhook_inbox(inbox_id: str) -> None:
    """Process a single row from payment_webhook_inbox.

    Reads the raw webhook body, calls the appropriate business logic via
    ``PaymentWebhookService``, then marks the row ``done``.  On transient
    failures increments ``attempts``, schedules ``next_run_at`` with
    exponential backoff, and sets status to ``error``.  After
    ``_MAX_ATTEMPTS`` the row is moved to ``dead`` and no further retries
    are scheduled (manual replay via admin endpoint required).

    The task is idempotent: re-enqueueing the same ``inbox_id`` is safe
    because the inbox row is loaded with ``FOR UPDATE`` and its status is
    checked before processing.
    """
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.payment_webhook_inbox import PaymentWebhookInbox

    row_id = uuid.UUID(inbox_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PaymentWebhookInbox)
            .where(PaymentWebhookInbox.id == row_id)
            .with_for_update(skip_locked=True)
        )
        row = result.scalar_one_or_none()

        if row is None:
            logger.warning("webhook_inbox_row_missing", inbox_id=inbox_id)
            return

        if row.status in ("done", "dead"):
            logger.info(
                "webhook_inbox_already_terminal",
                inbox_id=inbox_id,
                status=row.status,
            )
            return

        row.status = "processing"
        row.attempts += 1
        await db.flush()

        try:
            await _dispatch(db, row)
            row.status = "done"
            row.last_error = None
            await db.commit()
            logger.info(
                "webhook_inbox_processed",
                inbox_id=inbox_id,
                provider=row.provider,
                external_event_key=row.external_event_key,
            )
        except Exception as exc:
            await db.rollback()

            async with AsyncSessionLocal() as db2:
                result2 = await db2.execute(
                    select(PaymentWebhookInbox)
                    .where(PaymentWebhookInbox.id == row_id)
                    .with_for_update()
                )
                row2 = result2.scalar_one_or_none()
                if row2 is None:
                    return
                row2.last_error = str(exc)[:2000]
                if row2.attempts >= _MAX_ATTEMPTS:
                    row2.status = "dead"
                    row2.next_run_at = None
                    logger.error(
                        "webhook_inbox_dead",
                        inbox_id=inbox_id,
                        provider=row2.provider,
                        attempts=row2.attempts,
                        error=str(exc),
                    )
                else:
                    row2.status = "error"
                    row2.next_run_at = _next_run_at(row2.attempts)
                    logger.warning(
                        "webhook_inbox_error_retry",
                        inbox_id=inbox_id,
                        provider=row2.provider,
                        attempts=row2.attempts,
                        next_run_at=str(row2.next_run_at),
                        error=str(exc),
                    )
                await db2.commit()
            raise


async def _dispatch(db: AsyncSession, row: PaymentWebhookInbox) -> None:
    """Route the inbox row to the correct webhook handler."""
    from sqlalchemy import select

    from app.models.subscriptions import Payment
    from app.services.payment_webhook_service import PaymentWebhookService

    provider = row.provider
    body = row.raw_body or {}
    svc = PaymentWebhookService(db)

    if provider == "yookassa":
        # Re-use existing YooKassa business logic; IP check already done in HTTP layer.
        event = body.get("event", "")
        obj = body.get("object", {})
        external_id = obj.get("id", "")

        result = await db.execute(
            select(Payment)
            .where(Payment.external_payment_id == external_id)
            .with_for_update()
        )
        payment = result.scalar_one_or_none()

        if not payment:
            metadata = obj.get("metadata", {})
            internal_id = metadata.get("internal_payment_id")
            if internal_id:
                result = await db.execute(
                    select(Payment)
                    .where(Payment.id == internal_id)
                    .with_for_update()
                )
                payment = result.scalar_one_or_none()

        if not payment:
            logger.warning(
                "webhook_inbox_payment_not_found",
                inbox_id=str(row.id),
                external_id=external_id,
            )
            return


        if event == "payment.succeeded":
            if not await svc._yookassa_api_allows_succeeded(str(external_id), payment):
                return
            await svc._handle_payment_succeeded(payment, obj)
        elif event == "payment.canceled":
            await svc._handle_payment_canceled(payment)
        elif event == "refund.succeeded":
            await svc._handle_refund_succeeded(payment)
        else:
            logger.info("webhook_inbox_unknown_event", event=event, inbox_id=str(row.id))

    else:
        logger.error(
            "webhook_inbox_unknown_provider",
            provider=provider,
            inbox_id=str(row.id),
        )
        raise ValueError(f"Unknown provider in webhook inbox: {provider!r}")


@broker.task(retry_on_error=False)
async def retry_stale_webhook_inbox_rows() -> None:
    """Scheduled task: re-enqueue inbox rows stuck in ``error`` status.

    Picks rows where ``next_run_at <= now`` and ``status = error`` (i.e.
    eligible for retry) and re-enqueues them.  Should be called by the
    scheduler every minute.
    """
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.payment_webhook_inbox import PaymentWebhookInbox

    async with AsyncSessionLocal() as db:
        now = datetime.now(UTC)
        result = await db.execute(
            select(PaymentWebhookInbox)
            .where(
                PaymentWebhookInbox.status == "error",
                PaymentWebhookInbox.next_run_at <= now,
            )
            .limit(50)
        )
        rows = result.scalars().all()

    for row in rows:
        await process_payment_webhook_inbox.kiq(str(row.id))
        logger.info("webhook_inbox_re_enqueued", inbox_id=str(row.id))
