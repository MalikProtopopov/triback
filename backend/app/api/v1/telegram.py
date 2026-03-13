"""Telegram router — binding status, code generation, webhook."""

from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.redis import get_redis
from app.core.security import require_role
from app.schemas.telegram import GenerateCodeResponse, TelegramBindingStatus
from app.services.telegram_service import TelegramService

router = APIRouter(prefix="/telegram")


@router.get(
    "/binding",
    response_model=TelegramBindingStatus,
    summary="Статус привязки Telegram",
    responses=error_responses(401, 403),
)
async def get_binding_status(
    payload: dict[str, Any] = require_role("doctor"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Показывает, привязан ли Telegram-аккаунт к профилю.

    - **401** — не авторизован
    - **403** — роль не doctor
    """
    svc = TelegramService()
    return await svc.get_binding_status(db, payload["sub"])


@router.post(
    "/generate-code",
    response_model=GenerateCodeResponse,
    status_code=201,
    summary="Сгенерировать код привязки",
    responses=error_responses(401, 403, 409),
)
async def generate_code(
    payload: dict[str, Any] = require_role("doctor"),
    db: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
) -> dict:
    """Генерирует одноразовый код для привязки Telegram через бота.

    - **401** — не авторизован
    - **403** — роль не doctor
    - **409** — Telegram уже привязан
    """
    svc = TelegramService()
    code, expires_at = await svc.generate_auth_code(db, payload["sub"], redis)
    bot_username = settings.TELEGRAM_BOT_TOKEN.split(":")[0] if ":" in settings.TELEGRAM_BOT_TOKEN else "bot"
    return {
        "auth_code": code,
        "expires_at": expires_at.isoformat(),
        "bot_link": f"https://t.me/{bot_username}?start={code}",
        "instruction": "Перейдите по ссылке и отправьте боту команду /start",
    }


@router.post(
    "/webhook",
    summary="Telegram bot webhook",
    include_in_schema=False,
)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
    db: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
) -> JSONResponse:
    """Принимает обновления от Telegram Bot API. Не вызывать напрямую."""
    if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        return JSONResponse(status_code=403, content={"ok": False})

    body = await request.json()
    svc = TelegramService()
    await svc.handle_webhook(db, redis, body)
    return JSONResponse(status_code=200, content={"ok": True})
