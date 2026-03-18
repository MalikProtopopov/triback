"""Doctor communication — send reminders and custom emails."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.profiles import DoctorProfile
from app.models.users import User
from app.tasks.email_tasks import send_custom_email, send_reminder_notification


class DoctorCommunicationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_profile_or_404(self, profile_id: UUID) -> DoctorProfile:
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")
        return profile

    async def send_reminder(
        self, profile_id: UUID, message: str | None = None
    ) -> None:
        dp = await self._get_profile_or_404(profile_id)
        user = await self.db.get(User, dp.user_id)
        if not user:
            raise NotFoundError("User not found")
        await send_reminder_notification.kiq(user.email, message)

    async def send_email(
        self, profile_id: UUID, subject: str, body: str
    ) -> None:
        dp = await self._get_profile_or_404(profile_id)
        user = await self.db.get(User, dp.user_id)
        if not user:
            raise NotFoundError("User not found")
        await send_custom_email.kiq(user.email, subject, body)
