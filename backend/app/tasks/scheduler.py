"""Scheduled / cron-style tasks — subscription reminders and expiry."""

from datetime import UTC, datetime

import structlog
from sqlalchemy import and_, select

from app.tasks import broker

logger = structlog.get_logger(__name__)


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
