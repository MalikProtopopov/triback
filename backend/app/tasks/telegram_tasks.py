"""Telegram tasks — admin notifications, channel management."""

import structlog

from app.tasks import broker

logger = structlog.get_logger(__name__)


async def _get_svc_async():
    from app.core.database import AsyncSessionLocal
    from app.services.telegram_integration_service import get_telegram_config
    from app.services.telegram_service import TelegramService

    async with AsyncSessionLocal() as db:
        config = await get_telegram_config(db)
        if config:
            return TelegramService(bot_token=config[0], owner_chat_id=config[1])
        return TelegramService()


@broker.task  # type: ignore[misc]
async def notify_admin_new_registration(user_id: str) -> None:
    """Notify admin chat about a new doctor registration."""
    from app.core.config import settings

    svc = await _get_svc_async()
    if not svc._token or not svc._owner_chat_id:
        logger.warning("telegram_not_configured")
        return

    text = f"Новая регистрация врача.\nUser ID: {user_id}"
    try:
        await svc.send_message(int(svc._owner_chat_id), text)
    except Exception:
        logger.exception("notify_admin_failed", user_id=user_id)


@broker.task  # type: ignore[misc]
async def add_user_to_channel(tg_user_id: int) -> None:
    """Add user to the private Telegram channel."""
    svc = await _get_svc_async()
    try:
        await svc.add_to_channel(tg_user_id)
    except Exception:
        logger.exception("add_to_channel_failed", tg_user_id=tg_user_id)


@broker.task  # type: ignore[misc]
async def remove_user_from_channel(tg_user_id: int) -> None:
    """Remove user from the private Telegram channel."""
    svc = await _get_svc_async()
    try:
        await svc.remove_from_channel(tg_user_id)
    except Exception:
        logger.exception("remove_from_channel_failed", tg_user_id=tg_user_id)


@broker.task  # type: ignore[misc]
async def notify_admin_payment_received(
    user_email: str, amount: float, product_type: str
) -> None:
    """Notify admin chat about a successful payment."""
    svc = await _get_svc_async()
    if not svc._token or not svc._owner_chat_id:
        logger.warning("telegram_not_configured")
        return

    text = (
        f"Оплата получена\n"
        f"Email: {user_email}\n"
        f"Сумма: {amount:.2f} ₽\n"
        f"Тип: {product_type}"
    )
    try:
        await svc.send_message(int(svc._owner_chat_id), text)
    except Exception:
        logger.exception("notify_admin_payment_failed", email=user_email)
