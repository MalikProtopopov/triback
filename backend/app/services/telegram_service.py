"""Telegram service — Bot API calls, user binding, webhook processing."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import SubscriptionStatus
from app.core.exceptions import ConflictError
from app.models.subscriptions import Subscription
from app.models.users import TelegramBinding

logger = structlog.get_logger(__name__)

_BASE_URL = "https://api.telegram.org/bot{token}"
_AUTH_CODE_TTL = 600


class TelegramService:
    def __init__(self) -> None:
        self._base = _BASE_URL.format(token=settings.TELEGRAM_BOT_TOKEN)

    # ── Bot API helpers ───────────────────────────────────────────

    async def send_message(self, chat_id: int, text: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
            resp.raise_for_status()
            return resp.json()

    async def add_to_channel(self, tg_user_id: int) -> None:
        """Unban (=add) user from the private Telegram channel."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/unbanChatMember",
                json={
                    "chat_id": settings.TELEGRAM_CHANNEL_ID,
                    "user_id": tg_user_id,
                    "only_if_banned": True,
                },
            )
            logger.info("add_to_channel", tg_user_id=tg_user_id, status=resp.status_code)

    async def remove_from_channel(self, tg_user_id: int) -> None:
        """Ban (=remove) user from the private Telegram channel."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/banChatMember",
                json={
                    "chat_id": settings.TELEGRAM_CHANNEL_ID,
                    "user_id": tg_user_id,
                    "revoke_messages": False,
                },
            )
            logger.info("remove_from_channel", tg_user_id=tg_user_id, status=resp.status_code)

    # ── Auth code generation ──────────────────────────────────────

    async def generate_auth_code(
        self,
        db: AsyncSession,
        user_id: str,
        redis: Redis,  # type: ignore[type-arg]
    ) -> tuple[str, datetime]:
        """Generate a 6-char auth code for Telegram binding.

        Returns (code, expires_at).
        """
        result = await db.execute(
            select(TelegramBinding).where(TelegramBinding.user_id == user_id)
        )
        binding = result.scalar_one_or_none()

        if binding and binding.tg_user_id:
            raise ConflictError("Telegram already linked")

        code = secrets.token_hex(3).upper()[:6]
        expires_at = datetime.now(UTC) + timedelta(seconds=_AUTH_CODE_TTL)

        if binding:
            binding.auth_code = code
            binding.auth_code_expires_at = expires_at
        else:
            binding = TelegramBinding(
                user_id=user_id,
                auth_code=code,
                auth_code_expires_at=expires_at,
            )
            db.add(binding)

        await db.flush()

        await redis.setex(f"tg_auth:{code}", _AUTH_CODE_TTL, user_id)
        await db.commit()

        return code, expires_at

    # ── Webhook processing ────────────────────────────────────────

    async def handle_webhook(
        self,
        db: AsyncSession,
        redis: Redis,  # type: ignore[type-arg]
        update: dict,
    ) -> None:
        """Process incoming Telegram Bot webhook update (expecting /start {code})."""
        message = update.get("message")
        if not message:
            return

        text: str = message.get("text", "")
        from_user = message.get("from", {})
        tg_user_id = from_user.get("id")
        tg_username = from_user.get("username", "")
        tg_chat_id = message.get("chat", {}).get("id")

        if not tg_user_id or not text.startswith("/start "):
            return

        code = text.split(" ", 1)[1].strip()
        if not code:
            return

        user_id = await redis.get(f"tg_auth:{code}")
        if not user_id:
            await self.send_message(tg_chat_id, "Код недействителен или истёк.")
            return

        result = await db.execute(
            select(TelegramBinding).where(
                TelegramBinding.user_id == user_id,
                TelegramBinding.auth_code == code,
            )
        )
        binding = result.scalar_one_or_none()
        if not binding:
            await self.send_message(tg_chat_id, "Код не найден в системе.")
            return

        await self._bind_user(db, redis, binding, tg_user_id, tg_username, tg_chat_id)

    async def _bind_user(
        self,
        db: AsyncSession,
        redis: Redis,  # type: ignore[type-arg]
        binding: TelegramBinding,
        tg_user_id: int,
        tg_username: str,
        tg_chat_id: int,
    ) -> None:
        old_auth_code = binding.auth_code

        binding.tg_user_id = tg_user_id
        binding.tg_username = tg_username
        binding.tg_chat_id = tg_chat_id
        binding.linked_at = datetime.now(UTC)
        binding.auth_code = None
        binding.auth_code_expires_at = None

        if old_auth_code:
            await redis.delete(f"tg_auth:{old_auth_code}")

        has_active_sub = (
            await db.execute(
                select(Subscription.id).where(
                    Subscription.user_id == binding.user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    or_(
                        Subscription.ends_at.is_(None),
                        Subscription.ends_at > func.now(),
                    ),
                )
            )
        ).scalar_one_or_none()

        if has_active_sub:
            await self.add_to_channel(tg_user_id)
            binding.is_in_channel = True

        await db.commit()
        await self.send_message(tg_chat_id, "Telegram успешно привязан! ✅")

    # ── Binding status ────────────────────────────────────────────

    async def get_binding_status(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> dict:
        result = await db.execute(
            select(TelegramBinding).where(TelegramBinding.user_id == user_id)
        )
        binding = result.scalar_one_or_none()

        if not binding or not binding.tg_user_id:
            return {"is_linked": False, "tg_username": None, "is_in_channel": False}

        return {
            "is_linked": True,
            "tg_username": binding.tg_username,
            "is_in_channel": binding.is_in_channel,
        }
