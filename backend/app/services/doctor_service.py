"""DoctorAdminService — thin facade delegating to focused sub-services.

Kept for backward-compatibility with existing router imports.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.doctor_admin import (
    AdminCreateDoctorResponse,
    DoctorDetailResponse,
    ImportStatusResponse,
    PortalUserDetailResponse,
)
from app.services.doctor_communication_service import DoctorCommunicationService
from app.services.doctor_crud_service import DoctorCrudService
from app.services.doctor_import_service import DoctorImportService
from app.services.doctor_moderation_service import DoctorModerationService
from app.services.portal_user_service import PortalUserService


class DoctorAdminService:
    """Facade that preserves the original API surface for the admin router."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._crud = DoctorCrudService(db)
        self._moderation = DoctorModerationService(db)
        self._import = DoctorImportService(db)
        self._portal = PortalUserService(db)
        self._comms = DoctorCommunicationService(db)

    # ── CRUD ──────────────────────────────────────────────────────

    async def create_doctor(self, data: dict[str, Any]) -> AdminCreateDoctorResponse:
        return await self._crud.create_doctor(data)

    async def list_doctors(self, **kwargs: Any) -> dict[str, Any]:
        return await self._crud.list_doctors(**kwargs)

    async def get_doctor(self, profile_id: UUID) -> DoctorDetailResponse:
        return await self._crud.get_doctor(profile_id)

    async def update_board_role(
        self, profile_id: UUID, board_role: str | None
    ) -> DoctorDetailResponse:
        return await self._crud.update_board_role(profile_id, board_role)

    # ── Moderation ────────────────────────────────────────────────

    async def moderate(
        self, profile_id: UUID, admin_id: UUID, action: str, comment: str | None = None
    ) -> str:
        return await self._moderation.moderate(profile_id, admin_id, action, comment)

    async def approve_draft(
        self,
        profile_id: UUID,
        admin_id: UUID,
        action: str,
        rejection_reason: str | None = None,
    ) -> str:
        return await self._moderation.approve_draft(
            profile_id, admin_id, action, rejection_reason
        )

    async def toggle_active(self, profile_id: UUID, admin_id: UUID, is_public: bool) -> bool:
        return await self._moderation.toggle_active(profile_id, admin_id, is_public)

    # ── Import ────────────────────────────────────────────────────

    async def start_import(self, file_bytes: bytes, redis: Any) -> str:
        return await self._import.start_import(file_bytes, redis)

    async def get_import_status(self, task_id: str, redis: Any) -> ImportStatusResponse:
        return await self._import.get_import_status(task_id, redis)

    # ── Portal users ──────────────────────────────────────────────

    async def list_portal_users(self, **kwargs: Any) -> dict[str, Any]:
        return await self._portal.list_portal_users(**kwargs)

    async def get_portal_user(self, user_id: UUID) -> PortalUserDetailResponse:
        return await self._portal.get_portal_user(user_id)

    # ── Communication ─────────────────────────────────────────────

    async def send_reminder(self, profile_id: UUID, message: str | None = None) -> None:
        return await self._comms.send_reminder(profile_id, message)

    async def send_email(self, profile_id: UUID, subject: str, body: str) -> None:
        return await self._comms.send_email(profile_id, subject, body)
