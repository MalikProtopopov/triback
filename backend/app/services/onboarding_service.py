"""Onboarding service — role selection, profile filling, document upload, submission."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppValidationError, ConflictError, NotFoundError
from app.core.utils import generate_unique_slug
from app.models.profiles import DoctorDocument, DoctorProfile, ModerationHistory
from app.models.users import Role, User, UserRoleAssignment
from app.services import file_service

DOCUMENT_TYPES = {"medical_diploma", "retraining_cert", "oncology_cert", "additional_cert"}


class OnboardingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_status(self, user_id: UUID) -> dict:
        """Compute current onboarding status and next_step."""
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")

        email_verified = user.email_verified_at is not None

        role_result = await self.db.execute(
            select(Role)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(UserRoleAssignment.user_id == user_id)
        )
        roles = role_result.scalars().all()
        role_names = [r.name for r in roles]

        has_doctor_role = "doctor" in role_names
        has_user_role = "user" in role_names
        role_chosen = has_doctor_role or has_user_role
        role = "doctor" if has_doctor_role else ("user" if has_user_role else None)

        profile_filled = False
        documents_uploaded = False
        has_medical_diploma = False
        moderation_status = None
        submitted_at = None
        rejection_comment = None
        is_submitted = False

        if has_doctor_role:
            profile_result = await self.db.execute(
                select(DoctorProfile).where(DoctorProfile.user_id == user_id)
            )
            profile = profile_result.scalar_one_or_none()
            if profile:
                profile_filled = bool(profile.first_name and profile.last_name and profile.phone)
                has_medical_diploma = profile.has_medical_diploma
                moderation_status = profile.status
                submitted_at = profile.onboarding_submitted_at
                is_submitted = submitted_at is not None

                doc_result = await self.db.execute(
                    select(DoctorDocument).where(
                        DoctorDocument.doctor_profile_id == profile.id
                    )
                )
                docs = doc_result.scalars().all()
                documents_uploaded = len(docs) > 0

                if moderation_status == "rejected":
                    mh_result = await self.db.execute(
                        select(ModerationHistory.comment)
                        .where(
                            and_(
                                ModerationHistory.entity_type == "doctor_profile",
                                ModerationHistory.entity_id == profile.id,
                                ModerationHistory.action == "reject",
                            )
                        )
                        .order_by(ModerationHistory.created_at.desc())
                        .limit(1)
                    )
                    rejection_comment = mh_result.scalar_one_or_none()

        next_step = self._compute_next_step(
            email_verified=email_verified,
            role_chosen=role_chosen,
            role=role,
            profile_filled=profile_filled,
            has_medical_diploma=has_medical_diploma,
            moderation_status=moderation_status,
            is_submitted=is_submitted,
        )

        return {
            "email_verified": email_verified,
            "role_chosen": role_chosen,
            "role": role,
            "profile_filled": profile_filled,
            "documents_uploaded": documents_uploaded,
            "has_medical_diploma": has_medical_diploma,
            "moderation_status": moderation_status,
            "submitted_at": submitted_at,
            "rejection_comment": rejection_comment,
            "next_step": next_step,
        }

    @staticmethod
    def _compute_next_step(
        *,
        email_verified: bool,
        role_chosen: bool,
        role: str | None,
        profile_filled: bool,
        has_medical_diploma: bool,
        moderation_status: str | None,
        is_submitted: bool,
    ) -> str:
        if not email_verified:
            return "verify_email"
        if not role_chosen:
            return "choose_role"
        if role != "doctor":
            return "completed"
        if not profile_filled:
            return "fill_profile"
        if not has_medical_diploma:
            return "upload_documents"
        if not is_submitted:
            return "submit"
        if moderation_status == "pending_review":
            return "await_moderation"
        if moderation_status in ("approved", "active"):
            return "completed"
        if moderation_status == "rejected":
            return "fill_profile"
        return "submit"

    async def choose_role(self, user_id: UUID, role: str) -> dict:
        """Assign a role to the user. If doctor, create an empty DoctorProfile."""
        role_names_result = await self.db.execute(
            select(Role.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(UserRoleAssignment.user_id == user_id)
        )
        current_role_names = list(role_names_result.scalars().all())

        if "doctor" in current_role_names or "user" in current_role_names:
            raise ConflictError("Роль уже выбрана")

        db_role = await self.db.execute(select(Role).where(Role.name == role))
        role_obj = db_role.scalar_one_or_none()
        if not role_obj:
            raise NotFoundError(f"Role '{role}' not found in database")

        assignment = UserRoleAssignment(user_id=user_id, role_id=role_obj.id)
        self.db.add(assignment)

        profile_id = None
        if role == "doctor":
            slug = await generate_unique_slug(self.db, DoctorProfile, "doctor")
            profile = DoctorProfile(
                user_id=user_id,
                first_name="",
                last_name="",
                phone="",
                status="pending_review",
                slug=slug,
            )
            self.db.add(profile)
            await self.db.flush()
            profile_id = profile.id

        await self.db.commit()

        next_step = "fill_profile" if role == "doctor" else "completed"
        message = (
            "Заполните анкету врача для прохождения модерации"
            if role == "doctor"
            else "Роль сохранена"
        )
        return {
            "message": message,
            "next_step": next_step,
            "profile_id": str(profile_id) if profile_id else None,
            "moderation_status": "pending_review" if role == "doctor" else None,
        }

    async def update_doctor_profile(self, user_id: UUID, data: dict) -> dict:
        """Partially update the doctor profile during onboarding."""
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        for field, value in data.items():
            if value is not None and hasattr(profile, field):
                setattr(profile, field, value)

        await self.db.commit()
        await self.db.refresh(profile)

        return {
            "message": "Анкета сохранена. Загрузите необходимые документы",
            "next_step": "upload_documents",
            "profile_id": str(profile.id),
            "moderation_status": profile.status,
        }

    async def upload_document(
        self,
        user_id: UUID,
        document_type: str,
        upload_file: UploadFile,
    ) -> DoctorDocument:
        """Upload a document to S3 and create a DoctorDocument record."""
        if document_type not in DOCUMENT_TYPES:
            raise AppValidationError(
                f"Недопустимый тип документа: {document_type}. "
                f"Допустимые: {', '.join(sorted(DOCUMENT_TYPES))}"
            )

        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        data = await upload_file.read()
        file_size = len(data)
        await upload_file.seek(0)

        s3_key = await file_service.upload_file(
            file=upload_file,
            path=f"doctors/{user_id}/documents",
            allowed_types=file_service.DOCUMENT_MIMES,
            max_size_mb=10,
        )

        doc = DoctorDocument(
            doctor_profile_id=profile.id,
            document_type=document_type,
            file_url=s3_key,
            original_filename=upload_file.filename or "unknown",
            file_size=file_size,
            mime_type=upload_file.content_type or "application/octet-stream",
        )
        self.db.add(doc)

        if document_type == "medical_diploma":
            profile.has_medical_diploma = True

        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def submit(self, user_id: UUID) -> dict:
        """Submit the doctor profile for moderation (initial or re-submit after rejection)."""
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        if profile.status not in ("pending_review", "rejected"):
            raise ConflictError("Заявка уже одобрена или находится на проверке")

        if not profile.first_name or not profile.last_name or not profile.phone:
            raise AppValidationError(
                "Обязательные поля не заполнены: ФИО и телефон"
            )

        if not profile.has_medical_diploma:
            raise AppValidationError(
                "Для отправки заявки необходимо загрузить диплом "
                "о высшем медицинском образовании"
            )

        profile.status = "pending_review"
        profile.onboarding_submitted_at = datetime.now(tz=UTC)
        await self.db.commit()

        return {
            "message": "Заявка отправлена на модерацию. Мы уведомим вас о результате",
            "next_step": "await_moderation",
            "profile_id": str(profile.id),
            "moderation_status": "pending_review",
        }
