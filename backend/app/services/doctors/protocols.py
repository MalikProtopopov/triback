"""Ports for doctor admin read/write (tests / DI)."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.schemas.doctor_admin import AdminCreateDoctorResponse, DoctorDetailResponse


class DoctorAdminWritePort(Protocol):
    async def create_doctor(self, data: dict[str, Any]) -> AdminCreateDoctorResponse: ...
    async def update_board_role(
        self, profile_id: UUID, board_role: str | None
    ) -> DoctorDetailResponse: ...


class DoctorAdminReadPort(Protocol):
    async def list_doctors(self, **kwargs: Any) -> dict[str, Any]: ...
    async def get_doctor(self, profile_id: UUID) -> DoctorDetailResponse: ...
