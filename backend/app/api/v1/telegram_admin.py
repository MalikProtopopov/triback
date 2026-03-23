"""Admin endpoints for Telegram integration configuration."""

from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.models.telegram_integration import TelegramIntegration
from app.schemas.telegram_admin import (
    TelegramIntegrationCreateRequest,
    TelegramIntegrationResponse,
    TelegramIntegrationUpdateRequest,
)
from app.services.telegram_integration_service import TelegramIntegrationService

router = APIRouter(prefix="/admin")

ADMIN_MANAGER = require_role("admin", "manager")


def _to_response_with_svc(
    row: TelegramIntegration, svc: TelegramIntegrationService
) -> TelegramIntegrationResponse:
    masked = None
    if row.bot_token_encrypted:
        token = svc._decrypt_token(row)
        masked = svc._mask_token(token) if token else "***"
    return TelegramIntegrationResponse(
        id=row.id,
        bot_username=row.bot_username,
        owner_chat_id=row.owner_chat_id,
        webhook_url=row.webhook_url,
        is_webhook_active=row.is_webhook_active,
        is_active=row.is_active,
        welcome_message=row.welcome_message,
        bot_token_masked=masked,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get(
    "/telegram/integration",
    response_model=TelegramIntegrationResponse | None,
    summary="Получить настройки Telegram",
    responses=error_responses(401, 403),
)
async def get_telegram_integration(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> TelegramIntegrationResponse | None:
    """Текущие настройки Telegram-интеграции или null.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    svc = TelegramIntegrationService(db)
    row = await svc.get_integration_any()
    if not row:
        return None
    return _to_response_with_svc(row, svc)


@router.post(
    "/telegram/integration",
    response_model=TelegramIntegrationResponse,
    status_code=201,
    summary="Создать/обновить Telegram-интеграцию",
    responses=error_responses(401, 403, 422),
)
async def create_telegram_integration(
    body: TelegramIntegrationCreateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> TelegramIntegrationResponse:
    """Создать интеграцию. Валидация через getMe, шифрование токена.

    При наличии PUBLIC_API_URL — авто-регистрация webhook.
    """
    svc = TelegramIntegrationService(db)
    row = await svc.create_or_update(
        bot_token=body.bot_token,
        owner_chat_id=body.owner_chat_id,
        welcome_message=body.welcome_message,
    )
    return _to_response_with_svc(row, svc)


@router.patch(
    "/telegram/integration",
    response_model=TelegramIntegrationResponse,
    summary="Обновить Telegram-интеграцию (частично)",
    responses=error_responses(401, 403, 404, 422),
)
async def update_telegram_integration(
    body: TelegramIntegrationUpdateRequest,
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> TelegramIntegrationResponse:
    """Частичное обновление настроек.

    - **404** — интеграция не настроена
    """
    svc = TelegramIntegrationService(db)
    data = body.model_dump(exclude_none=True)
    if not data:
        row = await svc.get_integration_any()
        if not row:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Integration not configured")
        return _to_response_with_svc(row, svc)
    row = await svc.partial_update(**data)
    return _to_response_with_svc(row, svc)


@router.delete(
    "/telegram/integration",
    status_code=204,
    summary="Удалить Telegram-интеграцию",
    responses=error_responses(401, 403, 404),
)
async def delete_telegram_integration(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Удалить интеграцию и webhook."""
    svc = TelegramIntegrationService(db)
    await svc.delete_integration()
    return Response(status_code=204)


@router.get(
    "/telegram/integration/webhook-url",
    summary="URL для webhook",
    responses=error_responses(401, 403, 404),
)
async def get_webhook_url(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Возвращает URL для настройки webhook в Telegram."""
    svc = TelegramIntegrationService(db)
    row = await svc.get_integration_any()
    if not row or not row.webhook_secret:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Integration not configured")
    return {"webhook_url": svc.get_webhook_url(row.webhook_secret)}


@router.post(
    "/telegram/integration/webhook",
    summary="Установить webhook",
    responses=error_responses(401, 403, 404, 422),
)
async def set_webhook(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Установить webhook в Telegram."""
    svc = TelegramIntegrationService(db)
    await svc.set_webhook()
    return {"ok": True}


@router.delete(
    "/telegram/integration/webhook",
    summary="Удалить webhook",
    responses=error_responses(401, 403, 404),
)
async def delete_webhook(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Удалить webhook из Telegram."""
    svc = TelegramIntegrationService(db)
    await svc.delete_webhook()
    return {"ok": True}


@router.post(
    "/telegram/integration/test",
    summary="Отправить тестовое сообщение",
    responses=error_responses(401, 403, 404),
)
async def send_test_message(
    payload: dict[str, Any] = ADMIN_MANAGER,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Отправить тестовое сообщение в owner_chat_id."""
    svc = TelegramIntegrationService(db)
    await svc.send_test_message()
    return {"ok": True}
