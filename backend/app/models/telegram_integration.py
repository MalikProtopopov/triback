"""Telegram integration model — singleton configuration for admin-configured bot."""

from sqlalchemy import BigInteger, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TelegramIntegration(Base, TimestampMixin):
    __tablename__ = "telegram_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    bot_token_encrypted: Mapped[str | None] = mapped_column(Text)
    bot_username: Mapped[str | None] = mapped_column(String(100))
    owner_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    webhook_secret: Mapped[str | None] = mapped_column(String(64))
    webhook_url: Mapped[str | None] = mapped_column(String(512))
    is_webhook_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    welcome_message: Mapped[str | None] = mapped_column(Text)
