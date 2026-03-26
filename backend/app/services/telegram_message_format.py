"""HTML formatting for Telegram (parse_mode HTML) — structured messages, minimal decoration."""

from __future__ import annotations

import html
from typing import Any

from app.services.notification_user_context import UserContactContext

PRODUCT_TYPE_LABEL_RU: dict[str, str] = {
    "entry_fee": "Вступительный взнос",
    "subscription": "Членский взнос",
    "event": "Мероприятие",
    "membership_arrears": "Задолженность",
}


def tg_escape(text: Any) -> str:
    """Escape text for Telegram HTML mode."""
    if text is None:
        return ""
    return html.escape(str(text), quote=True)


def format_admin_alert(title: str, lines: list[tuple[str, str]]) -> str:
    """Build admin message: bold title, then Label: value lines."""
    parts: list[str] = [f"<b>{tg_escape(title)}</b>"]
    for label, value in lines:
        parts.append(f"{tg_escape(label)}: {tg_escape(value)}")
    return "\n".join(parts)


def format_user_notice(title: str, lines: list[tuple[str, str]]) -> str:
    """Build user-facing notice with bold title and structured lines."""
    parts: list[str] = [f"<b>{tg_escape(title)}</b>"]
    for label, value in lines:
        parts.append(f"{tg_escape(label)}: {tg_escape(value)}")
    return "\n".join(parts)


def contact_lines_for_admin(ctx: UserContactContext) -> list[tuple[str, str]]:
    """Standard identification block for admin Telegram alerts."""
    tg_display = f"@{ctx.telegram_username}" if ctx.telegram_username else "—"
    return [
        ("Email", ctx.email or "—"),
        ("ФИО", ctx.full_name or "—"),
        ("Телефон", ctx.phone or "—"),
        ("Telegram", tg_display),
        ("User ID", str(ctx.user_id)),
    ]


def product_type_ru(product_type: str) -> str:
    return PRODUCT_TYPE_LABEL_RU.get(product_type, product_type)
