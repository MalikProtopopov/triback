"""Admin service for event tariff management."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppValidationError, NotFoundError
from app.models.events import EventRegistration, EventTariff
from app.schemas.events_admin import TariffResponse


class EventTariffService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, event_id: UUID, data: dict[str, Any]) -> TariffResponse:
        from app.models.events import Event

        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")

        tariff = EventTariff(event_id=event_id, **data)
        self.db.add(tariff)
        await self.db.commit()
        await self.db.refresh(tariff)
        return self._to_response(tariff)

    async def update(
        self, event_id: UUID, tariff_id: UUID, data: dict[str, Any],
    ) -> TariffResponse:
        tariff = await self._get(event_id, tariff_id)

        new_limit = data.get("seats_limit")
        if new_limit is not None and new_limit < tariff.seats_taken:
            raise AppValidationError(
                f"seats_limit ({new_limit}) не может быть меньше seats_taken ({tariff.seats_taken})"
            )

        for field, value in data.items():
            if value is not None and hasattr(tariff, field):
                setattr(tariff, field, value)

        await self.db.commit()
        await self.db.refresh(tariff)
        return self._to_response(tariff)

    async def delete(self, event_id: UUID, tariff_id: UUID) -> None:
        tariff = await self._get(event_id, tariff_id)

        reg_count = (
            await self.db.execute(
                select(func.count(EventRegistration.id)).where(
                    EventRegistration.event_tariff_id == tariff_id
                )
            )
        ).scalar() or 0

        if reg_count > 0:
            raise AppValidationError(
                "Невозможно удалить тариф с привязанными регистрациями"
            )

        await self.db.delete(tariff)
        await self.db.commit()

    async def _get(self, event_id: UUID, tariff_id: UUID) -> EventTariff:
        result = await self.db.execute(
            select(EventTariff).where(
                and_(EventTariff.id == tariff_id, EventTariff.event_id == event_id)
            )
        )
        tariff = result.scalar_one_or_none()
        if not tariff:
            raise NotFoundError("Tariff not found")
        return tariff

    @staticmethod
    def _to_response(t: EventTariff) -> TariffResponse:
        return TariffResponse(
            id=t.id, event_id=t.event_id, name=t.name,
            description=t.description, conditions=t.conditions, details=t.details,
            price=float(t.price), member_price=float(t.member_price),
            benefits=t.benefits if isinstance(t.benefits, list) else [],
            seats_limit=t.seats_limit, seats_taken=t.seats_taken,
            is_active=t.is_active, sort_order=t.sort_order,
            created_at=t.created_at,
        )
