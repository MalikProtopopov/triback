"""Notification service — email/telegram dispatch, templates, cron reminders."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from jinja2 import BaseLoader, Environment
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import NotificationStatus, SubscriptionStatus
from app.models.subscriptions import Subscription
from app.models.users import Notification, NotificationTemplate, TelegramBinding, User

logger = structlog.get_logger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Low-level dispatch (stubs) ────────────────────────────────

    async def send_email(self, to: str, subject: str, body: str) -> None:
        from app.services.email_sender import send_smtp_email

        await send_smtp_email(to, subject, body)

    async def send_telegram(self, chat_id: int, text: str) -> None:
        """Stub: send Telegram message. Delegates to TelegramService."""
        from app.services.telegram_integration_service import get_telegram_config
        from app.services.telegram_service import TelegramService

        config = await get_telegram_config(self.db)
        if config:
            svc = TelegramService(bot_token=config[0], owner_chat_id=config[1])
        else:
            svc = TelegramService()
        await svc.send_message(chat_id, text)

    # ── Create notification record + dispatch ─────────────────────

    async def create_notification(
        self,
        *,
        user_id: UUID,
        template_code: str,
        channel: str,
        title: str,
        body: str,
        payload: dict[str, Any] | None = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            template_code=template_code,
            channel=channel,
            title=title,
            body=body,
            payload=payload,
            status=NotificationStatus.PENDING,
        )
        self.db.add(notif)
        await self.db.flush()

        try:
            if channel == "email":
                user = await self.db.get(User, user_id)
                if user:
                    await self.send_email(user.email, title, body)
            elif channel == "telegram":
                binding = (
                    await self.db.execute(
                        select(TelegramBinding).where(
                            TelegramBinding.user_id == user_id
                        )
                    )
                ).scalar_one_or_none()
                if binding and binding.tg_chat_id:
                    await self.send_telegram(binding.tg_chat_id, body)

            notif.status = "sent"  # type: ignore[assignment]
            notif.sent_at = datetime.now(UTC)
        except Exception:
            logger.exception("notification_dispatch_failed", notif_id=str(notif.id))
            notif.status = NotificationStatus.FAILED  # type: ignore[assignment]

        await self.db.commit()
        return notif

    # ── Template-based send ───────────────────────────────────────

    async def send_by_template(
        self,
        user_id: UUID,
        template_code: str,
        context: dict[str, Any],
    ) -> Notification | None:
        result = await self.db.execute(
            select(NotificationTemplate).where(
                and_(
                    NotificationTemplate.code == template_code,
                    NotificationTemplate.is_active.is_(True),
                )
            )
        )
        tpl = result.scalar_one_or_none()
        if not tpl:
            logger.warning("template_not_found", code=template_code)
            return None

        jinja_env = Environment(loader=BaseLoader(), autoescape=True)
        body = jinja_env.from_string(tpl.body_template).render(**context)

        title = tpl.subject or tpl.name

        return await self.create_notification(
            user_id=user_id,
            template_code=template_code,
            channel=tpl.channel,
            title=title,
            body=body,
            payload=context,
        )

    # ── Cron: subscription reminders ──────────────────────────────

    async def send_subscription_reminders(self) -> int:
        """Check active subscriptions expiring in 30/7/3/1 days; send reminders.

        Returns number of notifications created.
        """
        now = datetime.now(UTC)
        thresholds = {
            "reminder_30d": (29, 30),
            "reminder_7d": (6, 7),
            "reminder_3d": (2, 3),
            "reminder_last_day": (0, 1),
        }

        count = 0
        for template_code, (lo, hi) in thresholds.items():
            start = now + timedelta(days=lo)
            end = now + timedelta(days=hi)

            subs = (
                await self.db.execute(
                    select(Subscription).where(
                        and_(
                            Subscription.status == SubscriptionStatus.ACTIVE,
                            Subscription.ends_at >= start,
                            Subscription.ends_at < end,
                        )
                    )
                )
            ).scalars().all()

            for sub in subs:
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                existing = (
                    await self.db.execute(
                        select(func.count(Notification.id)).where(
                            and_(
                                Notification.user_id == sub.user_id,
                                Notification.template_code == template_code,
                                Notification.created_at >= today_start,
                            )
                        )
                    )
                ).scalar() or 0

                if existing > 0:
                    continue

                days_left = (sub.ends_at - now).days if sub.ends_at else 0
                await self.create_notification(
                    user_id=sub.user_id,
                    template_code=template_code,
                    channel="email",
                    title=f"Напоминание: подписка истекает через {days_left} дн.",
                    body=f"Ваша подписка истекает через {days_left} дней. Продлите членство.",
                )
                from app.tasks.telegram_tasks import notify_user_subscription_expiring

                await notify_user_subscription_expiring.kiq(str(sub.user_id), days_left)
                count += 1

        return count


async def run_daily_reminders(db: AsyncSession) -> None:
    """Standalone entry point for cron/TaskIQ scheduling."""
    svc = NotificationService(db)
    sent = await svc.send_subscription_reminders()
    logger.info("daily_reminders_complete", sent=sent)
