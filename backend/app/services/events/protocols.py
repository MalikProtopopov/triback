"""Ports for event admin submodules."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.schemas.events_admin import EventDetailResponse


class EventAdminCorePort(Protocol):
    async def list_events(self, **kwargs: Any) -> dict[str, Any]: ...
    async def get_event(self, event_id: UUID) -> EventDetailResponse: ...
    async def delete_event(self, event_id: UUID) -> None: ...
