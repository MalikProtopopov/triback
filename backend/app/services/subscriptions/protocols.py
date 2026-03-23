"""Ports for subscription pay / status."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.schemas.subscriptions import PayResponse, SubscriptionStatusResponse


class SubscriptionPayPort(Protocol):
    async def pay(
        self, user_id: UUID, plan_id: UUID, idempotency_key: str
    ) -> PayResponse: ...


class SubscriptionStatusPort(Protocol):
    async def get_status(self, user_id: UUID) -> SubscriptionStatusResponse: ...
