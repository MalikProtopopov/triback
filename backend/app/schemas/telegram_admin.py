"""Pydantic schemas for Telegram integration admin API."""

from datetime import datetime

from pydantic import BaseModel, Field


class TelegramIntegrationCreateRequest(BaseModel):
    bot_token: str = Field(..., min_length=1)
    owner_chat_id: int = Field(...)
    welcome_message: str | None = Field(None)


class TelegramIntegrationUpdateRequest(BaseModel):
    bot_token: str | None = Field(None, min_length=1)
    owner_chat_id: int | None = None
    is_active: bool | None = None
    welcome_message: str | None = None


class TelegramIntegrationResponse(BaseModel):
    id: int
    bot_username: str | None
    owner_chat_id: int | None
    webhook_url: str | None
    is_webhook_active: bool
    is_active: bool
    welcome_message: str | None
    bot_token_masked: str | None
    created_at: datetime
    updated_at: datetime
