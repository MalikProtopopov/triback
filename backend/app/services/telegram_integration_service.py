"""Telegram integration admin service — CRUD, webhook management, test message."""

from __future__ import annotations

import secrets
from typing import Any, cast

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import get_encryption
from app.core.exceptions import AppValidationError, NotFoundError
from app.models.site import SiteSetting
from app.models.telegram_integration import TelegramIntegration

logger = structlog.get_logger(__name__)

_BASE_URL = "https://api.telegram.org/bot{token}"
_INTEGRATION_ID = 1


async def _telegram_api(
    token: str,
    method: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call Telegram Bot API. Raises on HTTP error."""
    url = f"{_BASE_URL.format(token=token)}/{method}"
    async with httpx.AsyncClient(timeout=15) as client:
        if params:
            resp = await client.get(url, params=params)
        elif json_body:
            resp = await client.post(url, json=json_body)
        else:
            resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise AppValidationError(
                data.get("description", "Telegram API error")
            )
        return cast(dict[str, Any], data)


async def _validate_token(bot_token: str) -> str:
    """Validate token via getMe. Returns bot username (without @)."""
    data = await _telegram_api(bot_token, "getMe")
    user = data.get("result", {})
    username = user.get("username")
    if not username:
        raise AppValidationError("Bot has no username")
    return cast(str, username)


async def get_telegram_config(db: AsyncSession) -> tuple[str, int] | None:
    """Get (bot_token, owner_chat_id) from DB integration if present. Otherwise None (use env)."""
    svc = TelegramIntegrationService(db)
    row = await svc.get_integration()
    if not row:
        return None
    token = svc._decrypt_token(row)
    if not token or not row.owner_chat_id:
        return None
    return (token, row.owner_chat_id)


class TelegramIntegrationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.encryption = get_encryption()

    async def get_integration(self) -> TelegramIntegration | None:
        """Get active integration or None."""
        result = await self.db.execute(
            select(TelegramIntegration).where(
                TelegramIntegration.id == _INTEGRATION_ID,
                TelegramIntegration.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_integration_by_secret(self, webhook_secret: str) -> TelegramIntegration | None:
        """Get integration by webhook_secret for webhook handler."""
        result = await self.db.execute(
            select(TelegramIntegration).where(
                TelegramIntegration.webhook_secret == webhook_secret,
                TelegramIntegration.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_integration_any(self) -> TelegramIntegration | None:
        """Get integration regardless of is_active (for admin)."""
        result = await self.db.execute(
            select(TelegramIntegration).where(
                TelegramIntegration.id == _INTEGRATION_ID
            )
        )
        return result.scalar_one_or_none()

    def _decrypt_token(self, row: TelegramIntegration) -> str | None:
        if not row or not row.bot_token_encrypted:
            return None
        try:
            return self.encryption.decrypt(row.bot_token_encrypted)
        except Exception:
            logger.warning("token_decrypt_failed")
            return None

    def _mask_token(self, token: str) -> str:
        if len(token) < 12:
            return "***"
        return f"{token[:4]}...{token[-4:]}"

    async def create_or_update(
        self,
        *,
        bot_token: str,
        owner_chat_id: int,
        welcome_message: str | None = None,
        is_active: bool | None = None,
    ) -> TelegramIntegration:
        """Create or update integration. Validates token via getMe."""
        username = await _validate_token(bot_token)
        encrypted = self.encryption.encrypt(bot_token) if self.encryption.is_available else bot_token

        row = await self.get_integration_any()
        if row:
            row.bot_token_encrypted = encrypted
            row.bot_username = username
            row.owner_chat_id = owner_chat_id
            # Keep existing webhook_secret on update
            if welcome_message is not None:
                row.welcome_message = welcome_message
            if is_active is not None:
                row.is_active = is_active
        else:
            webhook_secret = secrets.token_urlsafe(32)[:64]
            row = TelegramIntegration(
                id=_INTEGRATION_ID,
                bot_token_encrypted=encrypted,
                bot_username=username,
                owner_chat_id=owner_chat_id,
                webhook_secret=webhook_secret,
                is_active=is_active if is_active is not None else True,
                welcome_message=welcome_message,
            )
            self.db.add(row)

        await self.db.flush()
        row.webhook_url = self.get_webhook_url(row.webhook_secret or "")

        if settings.PUBLIC_API_URL:
            await self._set_webhook(row)
        else:
            row.is_webhook_active = False

        await self._update_site_settings_bot_link(username)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def partial_update(
        self,
        *,
        bot_token: str | None = None,
        owner_chat_id: int | None = None,
        is_active: bool | None = None,
        welcome_message: str | None = None,
    ) -> TelegramIntegration:
        """Partial update. Validates bot_token via getMe if provided."""
        row = await self.get_integration_any()
        if not row:
            raise NotFoundError("Integration not configured")

        username = row.bot_username
        if bot_token:
            username = await _validate_token(bot_token)
            row.bot_token_encrypted = (
                self.encryption.encrypt(bot_token) if self.encryption.is_available else bot_token
            )
            row.bot_username = username
        if owner_chat_id is not None:
            row.owner_chat_id = owner_chat_id
        if is_active is not None:
            row.is_active = is_active
        if welcome_message is not None:
            row.welcome_message = welcome_message

        await self.db.flush()
        row.webhook_url = self.get_webhook_url(row.webhook_secret or "")

        if bot_token and settings.PUBLIC_API_URL:
            await self._set_webhook(row)

        if username:
            await self._update_site_settings_bot_link(username)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    def get_webhook_url(self, webhook_secret: str) -> str:
        """Build webhook URL for given secret."""
        base = (settings.PUBLIC_API_URL or "").rstrip("/")
        if not base:
            return ""
        return f"{base}/api/v1/telegram/webhook/{webhook_secret}"

    async def set_webhook(self) -> bool:
        """Set webhook in Telegram. Returns success."""
        row = await self.get_integration_any()
        if not row or not row.webhook_secret:
            raise NotFoundError("Integration not configured")
        token = self._decrypt_token(row)
        if not token:
            raise AppValidationError("Cannot decrypt bot token")
        url = self.get_webhook_url(row.webhook_secret)
        if not url:
            raise AppValidationError("PUBLIC_API_URL not set")

        await _telegram_api(
            token,
            "setWebhook",
            json_body={"url": url, "secret_token": row.webhook_secret},
        )
        row.is_webhook_active = True
        row.webhook_url = url
        await self.db.commit()
        return True

    async def delete_webhook(self) -> bool:
        """Delete webhook in Telegram. Returns success."""
        row = await self.get_integration_any()
        if not row:
            raise NotFoundError("Integration not configured")
        token = self._decrypt_token(row)
        if not token:
            raise AppValidationError("Cannot decrypt bot token")

        await _telegram_api(token, "deleteWebhook")
        row.is_webhook_active = False
        row.webhook_url = None
        await self.db.commit()
        return True

    async def delete_integration(self) -> None:
        """Delete integration and webhook."""
        row = await self.get_integration_any()
        if not row:
            raise NotFoundError("Integration not configured")
        token = self._decrypt_token(row)
        if token:
            try:
                await _telegram_api(token, "deleteWebhook")
            except Exception as e:
                logger.warning("delete_webhook_failed", error=str(e))
        await self.db.delete(row)
        await self.db.commit()

    async def send_test_message(self) -> bool:
        """Send test message to owner_chat_id. Returns success."""
        row = await self.get_integration_any()
        if not row or not row.owner_chat_id:
            raise NotFoundError("Integration not configured")
        token = self._decrypt_token(row)
        if not token:
            raise AppValidationError("Cannot decrypt bot token")

        await _telegram_api(
            token,
            "sendMessage",
            json_body={
                "chat_id": row.owner_chat_id,
                "text": "Тестовое сообщение от интеграции трихобэкенда.",
                "parse_mode": "HTML",
            },
        )
        return True

    async def _set_webhook(self, row: TelegramIntegration) -> None:
        """Register webhook in Telegram."""
        token = self._decrypt_token(row)
        if not token or not row.webhook_secret:
            return
        url = self.get_webhook_url(row.webhook_secret)
        if not url:
            return
        try:
            await _telegram_api(
                token,
                "setWebhook",
                json_body={"url": url, "secret_token": row.webhook_secret},
            )
            row.is_webhook_active = True
        except Exception as e:
            logger.warning("set_webhook_failed", error=str(e))
            row.is_webhook_active = False

    async def _update_site_settings_bot_link(self, bot_username: str) -> None:
        """Update site_settings.telegram_bot_link."""
        link = f"https://t.me/{bot_username}"
        result = await self.db.execute(
            select(SiteSetting).where(SiteSetting.key == "telegram_bot_link")
        )
        setting = result.scalar_one_or_none()
        value = {"url": link}  # Match spec format
        if setting:
            setting.value = value
        else:
            self.db.add(
                SiteSetting(key="telegram_bot_link", value=value)
            )
        await self.db.flush()
