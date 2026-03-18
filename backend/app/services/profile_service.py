"""Profile service — personal/public profile management, photo upload, draft moderation."""

from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ChangeStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.models.profiles import DoctorProfile, DoctorProfileChange
from app.services import file_service


class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Personal profile (private data, no moderation)
    # ------------------------------------------------------------------

    async def get_personal(self, user_id: UUID) -> DoctorProfile:
        result = await self.db.execute(
            select(DoctorProfile)
            .options(selectinload(DoctorProfile.city), selectinload(DoctorProfile.documents))
            .where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")
        return profile

    async def update_personal(self, user_id: UUID, data: dict) -> None:
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

    async def upload_diploma_photo(self, user_id: UUID, upload: UploadFile) -> str:
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        s3_key = await file_service.upload_file(
            file=upload,
            path=f"doctors/{user_id}/documents",
            allowed_types=file_service.IMAGE_MIMES,
            max_size_mb=5,
        )

        profile.diploma_photo_url = s3_key
        await self.db.commit()
        return s3_key

    # ------------------------------------------------------------------
    # Public profile (moderated changes via doctor_profile_changes)
    # ------------------------------------------------------------------

    async def get_public(self, user_id: UUID) -> dict:
        result = await self.db.execute(
            select(DoctorProfile)
            .options(selectinload(DoctorProfile.city))
            .where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        draft_result = await self.db.execute(
            select(DoctorProfileChange)
            .where(
                DoctorProfileChange.doctor_profile_id == profile.id,
                DoctorProfileChange.status == ChangeStatus.PENDING,
            )
        )
        draft = draft_result.scalar_one_or_none()

        if not draft:
            # Show rejected only if it's the most recent draft (no approved after it).
            # Otherwise we'd show stale rejection after a later approval.
            latest_result = await self.db.execute(
                select(DoctorProfileChange)
                .where(DoctorProfileChange.doctor_profile_id == profile.id)
                .order_by(desc(func.coalesce(
                    DoctorProfileChange.reviewed_at,
                    DoctorProfileChange.submitted_at,
                )))
                .limit(1)
            )
            latest = latest_result.scalar_one_or_none()
            if latest and latest.status in (ChangeStatus.REJECTED, ChangeStatus.APPROVED):
                draft = latest

        city_data = None
        if profile.city:
            city_data = {"id": profile.city.id, "name": profile.city.name}

        draft_data = None
        if draft:
            draft_data = {
                "status": draft.status,
                "changes": draft.changes,
                "submitted_at": draft.submitted_at,
                "rejection_reason": draft.rejection_reason,
                "reviewed_at": draft.reviewed_at,
            }

        return {
            "bio": profile.bio,
            "public_email": profile.public_email,
            "public_phone": profile.public_phone,
            "photo_url": file_service.build_media_url(profile.photo_url),
            "city": city_data,
            "clinic_name": profile.clinic_name,
            "academic_degree": profile.academic_degree,
            "pending_draft": draft_data,
        }

    async def update_public(self, user_id: UUID, data: dict) -> None:
        """Create a pending change request. Raises ConflictError if one already exists."""
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        moderation_comment = data.pop("moderation_comment", None)
        changes = {k: v for k, v in data.items() if v is not None}

        # Ensure JSON-serializable for JSONB (UUID, datetime → str)
        def _to_json_value(v: object) -> object:
            if isinstance(v, UUID):
                return str(v)
            if hasattr(v, "isoformat"):  # datetime, date
                return v.isoformat()
            return v

        changes = {k: _to_json_value(v) for k, v in changes.items()}

        if not changes:
            raise NotFoundError("No fields to update")

        change = DoctorProfileChange(
            doctor_profile_id=profile.id,
            changes=changes,
            changed_fields=list(changes.keys()),
            status=ChangeStatus.PENDING,
            moderation_comment=moderation_comment,
        )
        self.db.add(change)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("Изменения уже на модерации. Дождитесь решения") from None

    # ------------------------------------------------------------------
    # Photo upload with resize
    # ------------------------------------------------------------------

    async def upload_photo(self, user_id: UUID, upload: UploadFile) -> dict:
        """Upload photo to S3 and create/merge a pending draft for moderation."""
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        main_key, _thumb_key = await file_service.upload_image_with_thumbnail(
            file=upload,
            path=f"doctors/{user_id}/photo",
            max_size_mb=5,
        )

        draft_result = await self.db.execute(
            select(DoctorProfileChange).where(
                and_(
                    DoctorProfileChange.doctor_profile_id == profile.id,
                    DoctorProfileChange.status == ChangeStatus.PENDING,
                )
            )
        )
        existing_draft = draft_result.scalar_one_or_none()

        if existing_draft:
            updated_changes = dict(existing_draft.changes)
            updated_changes["photo_url"] = main_key
            existing_draft.changes = updated_changes
            if "photo_url" not in existing_draft.changed_fields:
                existing_draft.changed_fields = [
                    *existing_draft.changed_fields, "photo_url"
                ]
        else:
            draft = DoctorProfileChange(
                doctor_profile_id=profile.id,
                changes={"photo_url": main_key},
                changed_fields=["photo_url"],
                status=ChangeStatus.PENDING,
            )
            self.db.add(draft)

        await self.db.commit()

        return {
            "photo_url": file_service.build_media_url(main_key),
            "pending_moderation": True,
        }
