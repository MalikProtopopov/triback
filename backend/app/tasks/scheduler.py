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
    _scheduler_tasks.append(
        asyncio.create_task(
            _run_periodic("poll_pending_payments", poll_pending_moneta_payments, 30),
            name="sched_poll_moneta",
        )
    )
    _scheduler_tasks.append(
        asyncio.create_task(
            _run_periodic(
                "deactivate_certs", deactivate_expired_certificates, 86400
            ),
            name="sched_deactivate_certs",
        )
    )
    _scheduler_tasks.append(
        asyncio.create_task(
            _run_periodic(
                "expiring_report", send_admin_expiring_subscriptions_report, 86400
            ),
            name="sched_expiring_report",
        )
    )
    _scheduler_tasks.append(
        asyncio.create_task(
            _run_periodic(
                "close_voting", close_expired_voting_sessions, 3600
            ),
            name="sched_close_voting",
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

        from app.models.certificates import Certificate

        expired_user_ids = []
        for sub in expired_subs:
            sub.status = "expired"  # type: ignore[assignment]
            deactivated += 1
            expired_user_ids.append(sub.user_id)

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

        if expired_user_ids:
            certs_result = await db.execute(
                select(Certificate).where(
                    and_(
                        Certificate.user_id.in_(expired_user_ids),
                        Certificate.certificate_type == "member",
                        Certificate.is_active.is_(True),
                    )
                )
            )
            for cert in certs_result.scalars().all():
                cert.is_active = False

        await db.commit()

    logger.info("deactivate_expired_done", deactivated=deactivated)
    return deactivated


@broker.task  # type: ignore[misc]
async def close_expired_voting_sessions() -> int:
    """Hourly: set status=closed for active voting sessions where ends_at < now."""
    from app.core.database import AsyncSessionLocal
    from app.models.voting import VotingSession

    now = datetime.now(UTC)
    closed = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(VotingSession).where(
                and_(
                    VotingSession.status == "active",
                    VotingSession.ends_at < now,
                )
            )
        )
        expired_sessions = result.scalars().all()

        for session in expired_sessions:
            session.status = "closed"  # type: ignore[assignment]
            closed += 1

        await db.commit()

    logger.info("close_expired_voting_sessions_done", closed=closed)
    return closed


@broker.task  # type: ignore[misc]
async def poll_pending_moneta_payments() -> int:
    """Every 30s: check pending Moneta payments via API and confirm if paid.

    Only checks payments older than 2 min with a known moneta_operation_id.
    Acts as fallback when Pay URL webhooks are not delivered (demo mode).
    """
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.subscriptions import Payment
    from app.services.payment_webhook_service import PaymentWebhookService

    if settings.PAYMENT_PROVIDER != "moneta":
        return 0

    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=2)
    confirmed = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Payment).where(
                and_(
                    Payment.status == "pending",
                    Payment.moneta_operation_id.isnot(None),
                    Payment.created_at < cutoff,
                    or_(
                        Payment.expires_at.is_(None),
                        Payment.expires_at > now,
                    ),
                )
            )
        )
        pending = result.scalars().all()

        if not pending:
            return 0

        from app.services.payment_providers.moneta_client import MonetaPaymentProvider

        provider = MonetaPaymentProvider()
        confirmed_statuses = {"SUCCEED", "TAKENIN_NOTSENT", "TAKENOUT"}

        for payment in pending:
            try:
                op_info = await provider.get_operation_status(
                    payment.moneta_operation_id
                )
            except Exception as exc:
                logger.warning(
                    "poll_moneta_error",
                    payment_id=str(payment.id),
                    error=str(exc),
                )
                continue

            moneta_status = op_info.get("status", "unknown")
            attrs = op_info.get("attributes", {})
            has_children = str(attrs.get("haschildren", "0")) != "0"

            if moneta_status in confirmed_statuses or has_children:
                logger.info(
                    "poll_moneta_confirmed",
                    payment_id=str(payment.id),
                    moneta_status=moneta_status,
                )
                svc = PaymentWebhookService(db)
                await svc.handle_moneta_payment_succeeded(payment)
                confirmed += 1
            elif moneta_status in {"CANCELED", "REVERSED"}:
                logger.info(
                    "poll_moneta_canceled",
                    payment_id=str(payment.id),
                    moneta_status=moneta_status,
                )
                payment.status = "failed"  # type: ignore[assignment]
                payment.description = (
                    f"{payment.description or ''} | Отменено Moneta: {moneta_status}"
                ).strip(" |")
                from app.models.subscriptions import Subscription

                if payment.subscription_id:
                    sub = await db.get(Subscription, payment.subscription_id)
                    if sub and sub.status == "pending_payment":
                        sub.status = "cancelled"  # type: ignore[assignment]
                await db.commit()

    logger.info("poll_pending_moneta_done", checked=len(pending), confirmed=confirmed)
    return confirmed


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
    from app.services.payment_webhook_service import PaymentWebhookService

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

        webhook_svc = PaymentWebhookService(db)
        for payment in stale_payments:
            payment.status = "expired"  # type: ignore[assignment]
            expired_count += 1

            if payment.subscription_id:
                sub = await db.get(Subscription, payment.subscription_id)
                if sub and sub.status == "pending_payment":
                    sub.status = "cancelled"  # type: ignore[assignment]

            if payment.event_registration_id:
                await webhook_svc._cancel_event_registration(payment)

        await db.commit()

    logger.info("expire_stale_payments_done", expired=expired_count)
    return expired_count


@broker.task  # type: ignore[misc]
async def send_admin_expiring_subscriptions_report() -> int:
    """Daily: send admin a Telegram report of subscriptions expiring in the next 7 days.

    Each line: ФИО | email | дата окончания.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.subscriptions import Subscription
    from app.models.users import User
    from app.tasks.telegram_tasks import _get_svc_async

    now = datetime.now(UTC)
    cutoff = now + timedelta(days=7)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription, User).join(User, User.id == Subscription.user_id).where(
                and_(
                    Subscription.status == "active",
                    Subscription.ends_at.isnot(None),
                    Subscription.ends_at >= now,
                    Subscription.ends_at <= cutoff,
                )
            )
        )
        rows = result.all()

    if not rows:
        logger.info("admin_expiring_report_empty")
        return 0

    lines = ["Подписки истекают в ближайшие 7 дней:\n"]
    for sub, user in rows:
        dp_result = None
        full_name = user.email
        # Try to get full name from doctor profile
        try:
            from app.core.database import AsyncSessionLocal as _ASL
            from app.models.profiles import DoctorProfile

            async with _ASL() as db2:
                dp = (
                    await db2.execute(
                        select(DoctorProfile).where(DoctorProfile.user_id == user.id)
                    )
                ).scalar_one_or_none()
                if dp and (dp.first_name or dp.last_name):
                    full_name = f"{dp.first_name or ''} {dp.last_name or ''}".strip()
        except Exception:
            pass
        end_str = sub.ends_at.strftime("%d.%m.%Y") if sub.ends_at else "—"
        lines.append(f"• {full_name} | {user.email} | {end_str}")

    text = "\n".join(lines)

    svc = await _get_svc_async()
    if not svc._token or not svc._owner_chat_id:
        logger.warning("telegram_not_configured_for_report")
        return 0

    try:
        await svc.send_message(int(svc._owner_chat_id), text)
    except Exception:
        logger.exception("send_admin_expiring_report_failed")
        return 0

    logger.info("admin_expiring_report_sent", count=len(rows))
    return len(rows)


@broker.task  # type: ignore[misc]
async def deactivate_expired_certificates() -> int:
    """Daily: deactivate member certificates whose owners have no active subscription.

    Catches certificates that were missed by the inline deactivation in
    ``deactivate_expired_subscriptions`` (e.g. manual subscription changes).
    """
    from app.core.database import AsyncSessionLocal
    from app.models.certificates import Certificate
    from app.models.subscriptions import Subscription

    now = datetime.now(UTC)
    deactivated = 0

    async with AsyncSessionLocal() as db:
        active_sub_user_ids = (
            select(Subscription.user_id)
            .where(
                and_(
                    Subscription.status == "active",
                    or_(
                        Subscription.ends_at.is_(None),
                        Subscription.ends_at > now,
                    ),
                )
            )
            .correlate(None)
        )

        result = await db.execute(
            select(Certificate).where(
                and_(
                    Certificate.certificate_type == "member",
                    Certificate.is_active.is_(True),
                    Certificate.user_id.notin_(active_sub_user_ids),
                )
            )
        )
        stale_certs = result.scalars().all()

        for cert in stale_certs:
            cert.is_active = False
            deactivated += 1

        await db.commit()

    logger.info("deactivate_expired_certificates_done", deactivated=deactivated)
    return deactivated
