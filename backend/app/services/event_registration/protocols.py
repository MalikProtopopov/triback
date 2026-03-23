"""Ports for event registration sub-flows (testing / future DI)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class EventGuestRegistrationPort(Protocol):
    db: AsyncSession

    async def confirm_guest_registration(
        self, event_id: UUID, body: Any
    ) -> Any: ...


class EventMemberRegistrationPort(Protocol):
    db: AsyncSession

    async def register_authenticated(
        self, event_id: UUID, user_id: UUID, body: Any
    ) -> Any: ...


class EventRegistrationPaymentPort(Protocol):
    async def process_payment_for_registration(
        self, registration_id: UUID, user_id: UUID
    ) -> Any: ...
