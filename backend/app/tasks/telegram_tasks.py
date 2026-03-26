"""Telegram tasks — admin notifications, channel management, user notifications."""

from __future__ import annotations

import structlog
from uuid import UUID

from sqlalchemy import select

from app.core.logging_privacy import mask_email_for_log
from app.services.notification_user_context import build_user_contact_context
from app.services.telegram_message_format import (
    contact_lines_for_admin,
    format_admin_alert,
    format_user_notice,
    product_type_ru,
    tg_escape,
)
from app.services.telegram_service import TelegramService
from app.tasks import broker

logger = structlog.get_logger(__name__)


async def _get_svc_async() -> TelegramService:
    from app.core.database import AsyncSessionLocal
    from app.services.telegram_integration_service import get_telegram_config

    async with AsyncSessionLocal() as db:
        config = await get_telegram_config(db)
        if config:
            return TelegramService(bot_token=config[0], owner_chat_id=config[1])
        return TelegramService()


async def _load_contact_context(user_id: str):
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return await build_user_contact_context(db, UUID(user_id))


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


@broker.task
async def notify_admin_new_registration(user_id: str) -> None:
    """Notify admin chat about a new doctor registration."""

    svc = await _get_svc_async()
    if not svc._token or not svc._owner_chat_id:
        logger.warning("telegram_not_configured")
        return

    ctx = await _load_contact_context(user_id)
    text = format_admin_alert("Новая регистрация врача", contact_lines_for_admin(ctx))

    try:
        await svc.send_message(int(svc._owner_chat_id), text)
    except Exception:
        logger.exception("notify_admin_failed", user_id=user_id)


@broker.task
async def add_user_to_channel(tg_user_id: int) -> None:
    """Add user to the private Telegram channel."""
    svc = await _get_svc_async()
    try:
        await svc.add_to_channel(tg_user_id)
    except Exception:
        logger.exception("add_to_channel_failed", tg_user_id=tg_user_id)


@broker.task
async def remove_user_from_channel(tg_user_id: int) -> None:
    """Remove user from the private Telegram channel."""
    svc = await _get_svc_async()
    try:
        await svc.remove_from_channel(tg_user_id)
    except Exception:
        logger.exception("remove_from_channel_failed", tg_user_id=tg_user_id)


@broker.task
async def notify_user_moderation_result(
    user_id: str, status: str, comment: str | None = None
) -> None:
    """Notify user via Telegram about their onboarding moderation result."""
    if status == "approved":
        status_ru = "Одобрено"
    elif status == "rejected":
        status_ru = "Отклонено"
    else:
        status_ru = status
    lines: list[tuple[str, str]] = [("Статус", status_ru)]
    if comment:
        lines.append(("Комментарий", comment))
    text = format_user_notice("Результат проверки анкеты", lines)
    await _send_to_user(user_id, text)


@broker.task
async def notify_user_draft_result(
    user_id: str, status: str, rejection_reason: str | None = None
) -> None:
    """Notify user via Telegram about their public profile draft moderation result."""
    if status == "approve":
        title = "Публичный профиль"
        lines = [("Статус", "Одобрен и опубликован")]
    else:
        title = "Публичный профиль"
        lines = [("Статус", "Требуются правки")]
        if rejection_reason:
            lines.append(("Причина", rejection_reason))
    text = format_user_notice(title, lines)
    await _send_to_user(user_id, text)


@broker.task
async def notify_user_payment_succeeded(
    user_id: str, amount: float, product_type: str
) -> None:
    """Notify user via Telegram about successful payment."""
    lines = [
        ("Сумма", f"{amount:.2f} ₽"),
        ("Тип", product_type_ru(product_type)),
    ]
    text = format_user_notice("Оплата прошла успешно", lines)
    await _send_to_user(user_id, text)


@broker.task
async def notify_user_payment_failed(user_id: str) -> None:
    """Notify user via Telegram about failed payment."""
    text = format_user_notice(
        "Платёж не выполнен",
        [
            (
                "Действие",
                "Попробуйте снова или свяжитесь с поддержкой.",
            ),
        ],
    )
    await _send_to_user(user_id, text)


@broker.task
async def notify_user_event_ticket(
    user_id: str, event_title: str, event_date: str, amount: float
) -> None:
    """Notify user via Telegram about purchased event ticket."""
    lines = [
        ("Мероприятие", event_title),
        ("Дата", event_date),
        ("Сумма", f"{amount:.2f} ₽"),
    ]
    text = format_user_notice("Билет на мероприятие оформлен", lines)
    await _send_to_user(user_id, text)


@broker.task
async def notify_user_receipt_available(user_id: str, amount: float) -> None:
    """Notify user via Telegram that their receipt is ready."""
    lines = [
        ("Сумма", f"{amount:.2f} ₽"),
        ("Где смотреть", "Личный кабинет"),
    ]
    text = format_user_notice("Чек сформирован", lines)
    await _send_to_user(user_id, text)


@broker.task
async def notify_user_manual_reminder(user_id: str, message: str | None = None) -> bool:
    """Send manual reminder from admin to user's Telegram. Returns True if sent."""
    if message:
        body = f"<b>Напоминание</b>\n{tg_escape(message)}"
    else:
        body = format_user_notice(
            "Напоминание",
            [("Текст", "Подписка скоро истекает — продлите членство в личном кабинете.")],
        )
    return await _send_to_user(user_id, body)


@broker.task
async def notify_user_subscription_expiring(user_id: str, days_left: int) -> None:
    """Notify user via Telegram that their subscription is expiring soon."""
    lines = [
        ("Осталось дней", str(days_left)),
        ("Действие", "Продлите подписку в личном кабинете."),
    ]
    text = format_user_notice("Подписка скоро истекает", lines)
    await _send_to_user(user_id, text)


@broker.task
async def notify_admin_new_draft(user_id: str, full_name: str) -> None:
    """Notify admin chat about a new public profile draft submitted for review."""
    svc = await _get_svc_async()
    if not svc._token or not svc._owner_chat_id:
        logger.warning("telegram_not_configured")
        return

    ctx = await _load_contact_context(user_id)
    lines: list[tuple[str, str]] = [("Врач (черновик)", full_name)]
    if ctx:
        lines.extend(contact_lines_for_admin(ctx))
    else:
        lines.append(("User ID", user_id))

    text = format_admin_alert("Новый черновик на модерацию", lines)
    try:
        await svc.send_message(int(svc._owner_chat_id), text)
    except Exception:
        logger.exception("notify_admin_new_draft_failed", user_id=user_id)


@broker.task
async def notify_admin_payment_received(
    user_id: str,
    user_email: str,
    amount: float,
    product_type: str,
) -> None:
    """Notify admin chat about a successful payment."""
    svc = await _get_svc_async()
    if not svc._token or not svc._owner_chat_id:
        logger.warning("telegram_not_configured")
        return

    ctx = await _load_contact_context(user_id)
    lines: list[tuple[str, str]] = [
        ("Сумма", f"{amount:.2f} ₽"),
        ("Тип оплаты", product_type_ru(str(product_type))),
        ("Email (платёж)", user_email),
    ]
    if ctx:
        lines.extend(contact_lines_for_admin(ctx))
    else:
        lines.append(("User ID", user_id))

    text = format_admin_alert("Оплата получена", lines)
    try:
        await svc.send_message(int(svc._owner_chat_id), text)
    except Exception:
        logger.exception(
            "notify_admin_payment_failed",
            email_masked=mask_email_for_log(user_email),
        )
