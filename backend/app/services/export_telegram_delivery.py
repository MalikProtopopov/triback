"""Deliver generated XLSX exports to a configured Telegram chat."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.services.telegram_service import TelegramService


def resolve_exports_chat_id() -> int:
    """Chat or channel ID (may be negative for supergroups/channels)."""
    raw = (settings.TELEGRAM_EXPORTS_CHAT_ID or settings.TELEGRAM_CHANNEL_ID or "").strip()
    if not raw:
        raise HTTPException(
            status_code=503,
            detail="Не настроен TELEGRAM_EXPORTS_CHAT_ID или TELEGRAM_CHANNEL_ID",
        )
    try:
        return int(raw)
    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail="Некорректный ID чата Telegram для выгрузок",
        ) from e


async def deliver_xlsx_to_telegram(
    *,
    data: bytes,
    filename: str,
    caption: str,
) -> dict[str, Any]:
    chat_id = resolve_exports_chat_id()
    svc = TelegramService()
    try:
        return await svc.send_document(chat_id, data, filename, caption=caption)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Не удалось отправить файл в Telegram: {e!s}",
        ) from e
