"""Event registration service — register, pay, manage seats (facade)."""

from __future__ import annotations

from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EventStatus
from app.core.exceptions import AppValidationError, NotFoundError
from app.models.events import Event, EventTariff
from app.schemas.event_registration import (
    ConfirmGuestRegistrationRequest,
    RegisterForEventRequest,
    RegisterForEventResponse,
)
from app.services.event_registration import guest_flow, member_flow
from app.services.event_registration.runtime import EventRegistrationRuntime
from app.services.payment_providers import get_provider


class EventRegistrationService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis
        self.provider = get_provider()
        self._rt = EventRegistrationRuntime(db=db, redis=redis, provider=self.provider)

    async def register(
        self,
        event_id: UUID,
        user_id: UUID | None,
        body: RegisterForEventRequest,
    ) -> RegisterForEventResponse:
        tariff = await self.db.get(EventTariff, body.tariff_id)
        if not tariff or tariff.event_id != event_id:
            raise NotFoundError("Tariff not found for this event")
        if not tariff.is_active:
            raise AppValidationError("This tariff is no longer available")

        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")
        if event.status not in (EventStatus.UPCOMING, EventStatus.ONGOING):
            raise AppValidationError("Registration is closed for this event")

        if tariff.seats_limit is not None and tariff.seats_taken >= tariff.seats_limit:
            raise AppValidationError("No seats available for this tariff")

        if user_id:
            return await member_flow.register_authenticated(
                self._rt, event, tariff, user_id, body
            )

        if not body.guest_email:
            raise AppValidationError("Email is required for guest registration")

        from app.models.users import User

        existing = (
            await self.db.execute(select(User).where(User.email == body.guest_email))
        ).scalar_one_or_none()

        if existing:
            return await guest_flow.send_verification_code(
                self._rt, event, body, existing_user_id=existing.id,
            )

        return await guest_flow.send_verification_code(self._rt, event, body)

    async def confirm_guest_registration(
        self,
        event_id: UUID,
        body: ConfirmGuestRegistrationRequest,
    ) -> RegisterForEventResponse:
        return await guest_flow.confirm_guest_registration(self._rt, event_id, body)
