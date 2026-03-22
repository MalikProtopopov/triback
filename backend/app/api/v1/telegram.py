"""Telegram router — binding status, code generation, webhook."""

import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.redis import get_redis
from app.core.security import require_role
from app.schemas.telegram import GenerateCodeResponse, TelegramBindingStatus
from app.services.telegram_integration_service import TelegramIntegrationService
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
    # bot_username from integration or env
    int_svc = TelegramIntegrationService(db)
    integration = await int_svc.get_integration()
    bot_username = integration.bot_username if integration else None
    if not bot_username and settings.TELEGRAM_BOT_TOKEN and ":" in settings.TELEGRAM_BOT_TOKEN:
        bot_username = settings.TELEGRAM_BOT_TOKEN.split(":")[0]
    if not bot_username:
        bot_username = "bot"
    return {
        "auth_code": code,
        "expires_at": expires_at.isoformat(),
        "bot_link": f"https://t.me/{bot_username}?start={code}",
        "instruction": "Перейдите по ссылке и отправьте боту команду /start",
    }


@router.post(
    "/webhook/{webhook_secret}",
    summary="Telegram bot webhook (secret in URL)",
    include_in_schema=False,
)
async def telegram_webhook_with_secret(
    request: Request,
    webhook_secret: str = Path(...),
    x_telegram_bot_api_secret_token: str | None = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
) -> JSONResponse:
    """Принимает обновления от Telegram Bot API. Secret в URL.

    Валидация: X-Telegram-Bot-Api-Secret-Token должен совпадать с secret из path.
    """
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(webhook_secret, x_telegram_bot_api_secret_token):
        return JSONResponse(status_code=403, content={"ok": False})

    int_svc = TelegramIntegrationService(db)
    integration = await int_svc.get_integration_by_secret(webhook_secret)
    if not integration:
        return JSONResponse(status_code=403, content={"ok": False})

    body = await request.json()
    token = int_svc._decrypt_token(integration)
    owner_chat_id = integration.owner_chat_id or 0
    if not token:
        return JSONResponse(status_code=503, content={"ok": False})
    svc = TelegramService(bot_token=token, owner_chat_id=owner_chat_id)
    await svc.handle_webhook(db, redis, body)
    return JSONResponse(status_code=200, content={"ok": True})


@router.post(
    "/webhook",
    summary="Telegram bot webhook (legacy env-based)",
    include_in_schema=False,
)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
) -> JSONResponse:
    """Принимает обновления от Telegram Bot API. Обратная совместимость с env.

    Работает только если env задан и нет активной интеграции в БД.
    """
    int_svc = TelegramIntegrationService(db)
    integration = await int_svc.get_integration()
    if integration:
        # DB integration active — use webhook with secret in URL
        return JSONResponse(status_code=403, content={"ok": False})

    if settings.TELEGRAM_WEBHOOK_SECRET:
        if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
            settings.TELEGRAM_WEBHOOK_SECRET, x_telegram_bot_api_secret_token
        ):
            return JSONResponse(status_code=403, content={"ok": False})
    elif x_telegram_bot_api_secret_token:
        return JSONResponse(status_code=403, content={"ok": False})

    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHANNEL_ID:
        return JSONResponse(status_code=503, content={"ok": False})

    body = await request.json()
    svc = TelegramService()
    await svc.handle_webhook(db, redis, body)
    return JSONResponse(status_code=200, content={"ok": True})
