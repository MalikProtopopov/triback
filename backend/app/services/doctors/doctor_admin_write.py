"""Doctor admin write operations — create doctor, board role."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import DoctorStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging_privacy import mask_email_for_log
from app.core.security import hash_password
from app.core.utils import generate_unique_slug
from app.models.profiles import DoctorProfile, DoctorSpecialization
from app.models.users import Role, User, UserRoleAssignment
from app.schemas.doctor_admin import AdminCreateDoctorResponse, DoctorDetailResponse
from app.services.doctors.doctor_admin_read import DoctorAdminRead
from app.tasks.email_tasks import send_doctor_invite_email

logger = structlog.get_logger(__name__)


class DoctorAdminWrite:
    def __init__(self, db: AsyncSession, read: DoctorAdminRead) -> None:
        self.db = db
        self._read = read

    async def _get_profile_or_404(self, profile_id: UUID) -> DoctorProfile:
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")
        return profile

    async def create_doctor(self, data: dict[str, Any]) -> AdminCreateDoctorResponse:
        existing = await self.db.execute(
            select(User.id).where(User.email == data["email"])
        )
        if existing.scalar_one_or_none():
            raise ConflictError("User with this email already exists")

        doctor_role = (
            await self.db.execute(select(Role).where(Role.name == "doctor"))
        ).scalar_one_or_none()
        if not doctor_role:
            raise NotFoundError("Role 'doctor' not found in database")

        temp_password = f"Tmp{uuid4().hex[:12]}!"

        user = User(
            email=data["email"],
            password_hash=hash_password(temp_password),
            email_verified_at=datetime.now(UTC),
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

        self.db.add(UserRoleAssignment(user_id=user.id, role_id=doctor_role.id))

        slug = await generate_unique_slug(
            self.db, DoctorProfile, f"{data['last_name']} {data['first_name']}"
        )

        profile = DoctorProfile(
            user_id=user.id,
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data["phone"],
            middle_name=data.get("middle_name"),
            city_id=data.get("city_id"),
            clinic_name=data.get("clinic_name"),
            position=data.get("position"),
            academic_degree=data.get("academic_degree"),
            bio=data.get("bio"),
            public_email=data.get("public_email"),
            public_phone=data.get("public_phone"),
            status=data.get("status", DoctorStatus.APPROVED),
            slug=slug,
        )
        self.db.add(profile)
        await self.db.flush()

        spec_ids = data.get("specialization_ids") or []
        for sid in spec_ids:
            self.db.add(
                DoctorSpecialization(
                    doctor_profile_id=profile.id,
                    specialization_id=sid,
                )
            )

        await self.db.commit()

        if data.get("send_invite", True):
            await send_doctor_invite_email.kiq(
                data["email"], temp_password, settings.FRONTEND_URL
            )

        logger.info(
            "doctor_created_by_admin",
            user_id=str(user.id),
            profile_id=str(profile.id),
            email_masked=mask_email_for_log(data["email"]),
        )

        return AdminCreateDoctorResponse(
            user_id=user.id,
            profile_id=profile.id,
            email=user.email,
            first_name=profile.first_name,
            last_name=profile.last_name,
            status=profile.status,
            temp_password=temp_password if not data.get("send_invite", True) else None,
        )

    async def update_board_role(
        self, profile_id: UUID, board_role: str | None
    ) -> DoctorDetailResponse:
        dp = await self._get_profile_or_404(profile_id)
        dp.board_role = board_role
        await self.db.commit()
        await self.db.refresh(dp)
        return await self._read.get_doctor(profile_id)
