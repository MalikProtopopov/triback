"""Telegram tasks — admin notifications, channel management, user notifications."""

import structlog
from sqlalchemy import select

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


async def _send_to_user(user_id: str, text: str) -> bool:
    """Send Telegram message to user if they have a binding. Returns True if sent."""
    from app.core.database import AsyncSessionLocal
    from app.models.users import TelegramBinding

    svc = await _get_svc_async()
    if not svc._token:
        return False
    async with AsyncSessionLocal() as db:
        binding = (
            await db.execute(
                select(TelegramBinding).where(TelegramBinding.user_id == user_id)
            )
        ).scalar_one_or_none()
        if binding and binding.tg_chat_id:
            try:
                await svc.send_message(binding.tg_chat_id, text)
                return True
            except Exception:
                logger.exception("send_to_user_failed", user_id=user_id)
    return False


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
async def notify_user_moderation_result(
    user_id: str, status: str, comment: str | None = None
) -> None:
    """Notify user via Telegram about their onboarding moderation result."""
    status_text = "одобрен ✅" if status == "active" else "отклонён ❌"
    text = f"Ваша анкета была проверена.\nСтатус: {status_text}"
    if comment:
        text += f"\nКомментарий: {comment}"
    await _send_to_user(user_id, text)


@broker.task  # type: ignore[misc]
async def notify_user_draft_result(
    user_id: str, status: str, rejection_reason: str | None = None
) -> None:
    """Notify user via Telegram about their public profile draft moderation result."""
    if status == "approved":
        text = "Ваш публичный профиль одобрен и опубликован ✅"
    else:
        text = "Ваш публичный профиль требует правок ❌"
        if rejection_reason:
            text += f"\nПричина: {rejection_reason}"
    await _send_to_user(user_id, text)


@broker.task  # type: ignore[misc]
async def notify_user_payment_succeeded(
    user_id: str, amount: float, product_type: str
) -> None:
    """Notify user via Telegram about successful payment."""
    text = (
        f"Оплата прошла успешно ✅\n"
        f"Сумма: {amount:.2f} ₽\n"
        f"Тип: {product_type}"
    )
    await _send_to_user(user_id, text)


@broker.task  # type: ignore[misc]
async def notify_user_payment_failed(user_id: str) -> None:
    """Notify user via Telegram about failed payment."""
    text = "Платёж не удался ❌\nПожалуйста, попробуйте снова или свяжитесь с поддержкой."
    await _send_to_user(user_id, text)


@broker.task  # type: ignore[misc]
async def notify_user_event_ticket(
    user_id: str, event_title: str, event_date: str, amount: float
) -> None:
    """Notify user via Telegram about purchased event ticket."""
    text = (
        f"Билет на мероприятие оформлен ✅\n"
        f"Мероприятие: {event_title}\n"
        f"Дата: {event_date}\n"
        f"Сумма: {amount:.2f} ₽"
    )
    await _send_to_user(user_id, text)


@broker.task  # type: ignore[misc]
async def notify_user_receipt_available(user_id: str, amount: float) -> None:
    """Notify user via Telegram that their receipt is ready."""
    text = f"Ваш чек готов 🧾\nСумма: {amount:.2f} ₽\nЧек доступен в личном кабинете."
    await _send_to_user(user_id, text)


@broker.task  # type: ignore[misc]
async def notify_user_subscription_expiring(user_id: str, days_left: int) -> None:
    """Notify user via Telegram that their subscription is expiring soon."""
    text = (
        f"Ваша подписка истекает через {days_left} дн. ⏰\n"
        f"Не забудьте продлить её в личном кабинете."
    )
    await _send_to_user(user_id, text)


@broker.task  # type: ignore[misc]
async def notify_admin_new_draft(user_id: str, full_name: str) -> None:
    """Notify admin chat about a new public profile draft submitted for review."""
    svc = await _get_svc_async()
    if not svc._token or not svc._owner_chat_id:
        logger.warning("telegram_not_configured")
        return
    text = (
        f"Новый черновик на модерацию 📝\n"
        f"Врач: {full_name}\n"
        f"User ID: {user_id}"
    )
    try:
        await svc.send_message(int(svc._owner_chat_id), text)
    except Exception:
        logger.exception("notify_admin_new_draft_failed", user_id=user_id)


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
