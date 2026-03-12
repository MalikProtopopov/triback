"""Pydantic schemas for Telegram binding endpoints."""

from datetime import datetime

from pydantic import BaseModel


class TelegramBindingStatus(BaseModel):
    is_linked: bool
    tg_username: str | None = None
    is_in_channel: bool = False


class GenerateCodeResponse(BaseModel):
    auth_code: str
    expires_at: datetime
    bot_link: str
    instruction: str = "Перейдите по ссылке и отправьте боту команду /start"
