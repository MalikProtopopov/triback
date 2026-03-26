"""Load user contact fields for notification text and admin API (email, FIO, TG, phone)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profiles import DoctorProfile
from app.models.users import TelegramBinding, User


@dataclass(frozen=True)
class UserContactContext:
    user_id: UUID
    email: str
    full_name: str | None
    phone: str | None
    telegram_username: str | None


async def build_user_contact_context(
    db: AsyncSession, user_id: UUID
) -> UserContactContext:
    """Load email, doctor FIO/phone, and Telegram @username for a user."""
    user = await db.get(User, user_id)
    email = user.email if user else ""

    dp = (
        await db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
    ).scalar_one_or_none()
    full_name: str | None = None
    phone: str | None = None
    if dp:
        full_name = f"{dp.last_name or ''} {dp.first_name or ''}".strip() or None
        phone = dp.phone or None

    tg_raw = (
        await db.execute(
            select(TelegramBinding.tg_username).where(
                TelegramBinding.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    tg: str | None = None
    if tg_raw:
        s = str(tg_raw).strip().lstrip("@")
        tg = s or None

    return UserContactContext(
        user_id=user_id,
        email=email,
        full_name=full_name,
        phone=phone,
        telegram_username=tg,
    )
