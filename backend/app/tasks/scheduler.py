"""Scheduled / cron-style tasks — subscription reminders and expiry.

Tasks are registered as ``@broker.task`` for manual invocation via ``.kiq()``
and also run automatically via ``start_scheduler()`` which launches asyncio
background loops during application lifespan.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, or_, select

from app.tasks import broker

logger = structlog.get_logger(__name__)

_scheduler_tasks: list[asyncio.Task] = []  # type: ignore[type-arg]


async def _run_periodic(name: str, coro_fn, interval_seconds: int) -> None:  # noqa: ANN001
    """Run *coro_fn* every *interval_seconds*, catching exceptions."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            result = await coro_fn()
            logger.info(f"scheduler_{name}_ok", result=result)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception(f"scheduler_{name}_error")


async def start_scheduler() -> None:
    """Launch background loops — call from FastAPI lifespan startup."""
    _scheduler_tasks.append(
        asyncio.create_task(
            _run_periodic("expiry_check", deactivate_expired_subscriptions, 3600),
            name="sched_deactivate",
        )
    )
    _scheduler_tasks.append(
        asyncio.create_task(
            _run_periodic("reminder_check", check_expiring_subscriptions, 86400),
            name="sched_reminders",
        )
    )
    _scheduler_tasks.append(
        asyncio.create_task(
            _run_periodic("expire_payments", expire_stale_pending_payments, 1800),
            name="sched_expire_payments",
        )
    )
    logger.info("scheduler_started", tasks=len(_scheduler_tasks))


async def stop_scheduler() -> None:
    """Cancel background loops — call from FastAPI lifespan shutdown."""
    for t in _scheduler_tasks:
        t.cancel()
    await asyncio.gather(*_scheduler_tasks, return_exceptions=True)
    _scheduler_tasks.clear()
    logger.info("scheduler_stopped")


@broker.task  # type: ignore[misc]
async def check_expiring_subscriptions() -> int:
    """Daily: send email reminders for subscriptions expiring in 30/7/3/1 days.

    Delegates to ``NotificationService.send_subscription_reminders()`` which
    already de-duplicates (at most one notification per template per day per user).
    """
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        svc = NotificationService(db)
        sent = svc.send_subscription_reminders()
        count = await sent
        logger.info("check_expiring_subscriptions_done", sent=count)
        return count


@broker.task  # type: ignore[misc]
async def deactivate_expired_subscriptions() -> int:
    """Hourly: mark expired subscriptions and remove Telegram channel access.

    Finds subscriptions with status='active' and ends_at < now(), sets status
    to 'expired', and removes the user from the Telegram channel if bound.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.subscriptions import Subscription
    from app.models.users import TelegramBinding
    from app.tasks.telegram_tasks import remove_user_from_channel

    now = datetime.now(UTC)
    deactivated = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                and_(
                    Subscription.status == "active",
                    Subscription.ends_at < now,
                )
            )
        )
        expired_subs = result.scalars().all()

        for sub in expired_subs:
            sub.status = "expired"  # type: ignore[assignment]
            deactivated += 1

            binding_result = await db.execute(
                select(TelegramBinding).where(
                    and_(
                        TelegramBinding.user_id == sub.user_id,
                        TelegramBinding.is_in_channel.is_(True),
                    )
                )
            )
            binding = binding_result.scalar_one_or_none()
            if binding and binding.tg_user_id:
                await remove_user_from_channel.kiq(binding.tg_user_id)
                binding.is_in_channel = False

        await db.commit()

    logger.info("deactivate_expired_done", deactivated=deactivated)
    return deactivated


@broker.task  # type: ignore[misc]
async def expire_stale_pending_payments() -> int:
    """Every 30 min: mark pending payments past their expires_at as expired.

    Handles both:
    - payments with explicit expires_at in the past
    - legacy payments without expires_at but created > 24 h ago

    Also cancels linked subscriptions that are still in pending_payment state
    so the user can start a fresh payment flow.
    """
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.subscriptions import Payment, Subscription

    now = datetime.now(UTC)
    fallback_cutoff = now - timedelta(hours=settings.PAYMENT_EXPIRATION_HOURS)
    expired_count = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Payment).where(
                and_(
                    Payment.status == "pending",
                    or_(
                        and_(Payment.expires_at.isnot(None), Payment.expires_at < now),
                        and_(Payment.expires_at.is_(None), Payment.created_at < fallback_cutoff),
                    ),
                )
            )
        )
        stale_payments = result.scalars().all()

        for payment in stale_payments:
            payment.status = "expired"  # type: ignore[assignment]
            expired_count += 1

            if payment.subscription_id:
                sub = await db.get(Subscription, payment.subscription_id)
                if sub and sub.status == "pending_payment":
                    sub.status = "cancelled"  # type: ignore[assignment]

        await db.commit()

    logger.info("expire_stale_payments_done", expired=expired_count)
    return expired_count
