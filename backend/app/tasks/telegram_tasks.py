"""Telegram tasks — admin notifications, channel management."""

import structlog

from app.tasks import broker

logger = structlog.get_logger(__name__)


@broker.task  # type: ignore[misc]
async def notify_admin_new_registration(user_id: str) -> None:
    """Notify admin chat about a new doctor registration."""
    from app.core.config import settings
    from app.services.telegram_service import TelegramService

    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHANNEL_ID:
        logger.warning("telegram_not_configured")
        return

    svc = TelegramService()
    text = f"Новая регистрация врача.\nUser ID: {user_id}"
    try:
        await svc.send_message(int(settings.TELEGRAM_CHANNEL_ID), text)
    except Exception:
        logger.exception("notify_admin_failed", user_id=user_id)


@broker.task  # type: ignore[misc]
async def add_user_to_channel(tg_user_id: int) -> None:
    """Add user to the private Telegram channel."""
    from app.services.telegram_service import TelegramService

    svc = TelegramService()
    try:
        await svc.add_to_channel(tg_user_id)
    except Exception:
        logger.exception("add_to_channel_failed", tg_user_id=tg_user_id)


@broker.task  # type: ignore[misc]
async def remove_user_from_channel(tg_user_id: int) -> None:
    """Remove user from the private Telegram channel."""
    from app.services.telegram_service import TelegramService

    svc = TelegramService()
    try:
        await svc.remove_from_channel(tg_user_id)
    except Exception:
        logger.exception("remove_from_channel_failed", tg_user_id=tg_user_id)


@broker.task  # type: ignore[misc]
async def notify_admin_payment_received(
    user_email: str, amount: float, product_type: str
) -> None:
    """Notify admin chat about a successful payment."""
    from app.core.config import settings
    from app.services.telegram_service import TelegramService

    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHANNEL_ID:
        logger.warning("telegram_not_configured")
        return

    svc = TelegramService()
    text = (
        f"Оплата получена\n"
        f"Email: {user_email}\n"
        f"Сумма: {amount:.2f} ₽\n"
        f"Тип: {product_type}"
    )
    try:
        await svc.send_message(int(settings.TELEGRAM_CHANNEL_ID), text)
    except Exception:
        logger.exception("notify_admin_payment_failed", email=user_email)
