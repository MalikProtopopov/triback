"""Facade — same API as legacy DoctorCrudService."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.doctor_admin import (
    AdminCreateDoctorResponse,
    DoctorDetailResponse,
    DoctorPaymentOverridesRequest,
)
from app.services.doctors.doctor_admin_read import DoctorAdminRead
from app.services.doctors.doctor_admin_write import DoctorAdminWrite


class DoctorCrudService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._read = DoctorAdminRead(db)
        self._write = DoctorAdminWrite(db, self._read)

    async def create_doctor(self, data: dict[str, Any]) -> AdminCreateDoctorResponse:
        return await self._write.create_doctor(data)

    async def list_doctors(self, **kwargs: Any) -> dict[str, Any]:
        return await self._read.list_doctors(**kwargs)

    async def get_doctor(self, profile_id: UUID) -> DoctorDetailResponse:
        return await self._read.get_doctor(profile_id)

    async def update_board_role(
        self, profile_id: UUID, board_role: str | None
    ) -> DoctorDetailResponse:
        return await self._write.update_board_role(profile_id, board_role)

    async def update_payment_overrides(
        self, profile_id: UUID, body: DoctorPaymentOverridesRequest
    ) -> DoctorDetailResponse:
        return await self._write.update_payment_overrides(profile_id, body)
