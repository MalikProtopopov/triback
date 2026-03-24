"""Profile service — personal/public profile management, photo upload, draft moderation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.core.enums import ChangeStatus
from app.core.exceptions import AppValidationError, NotFoundError
from app.models.profiles import DoctorProfile, DoctorProfileChange
from app.schemas.profile import PublicProfileUpdate
from app.services import file_service


class _UnsetType:
    pass


_UNSET = _UnsetType()


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

    async def update_personal(self, user_id: UUID, data: dict[str, Any]) -> None:
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

    @staticmethod
    def _to_json_change_value(v: object) -> object:
        if isinstance(v, UUID):
            return str(v)
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return v

    async def _get_pending_draft(self, profile_id: UUID) -> DoctorProfileChange | None:
        r = await self.db.execute(
            select(DoctorProfileChange).where(
                and_(
                    DoctorProfileChange.doctor_profile_id == profile_id,
                    DoctorProfileChange.status == ChangeStatus.PENDING,
                )
            )
        )
        return r.scalar_one_or_none()

    async def _upsert_public_draft(
        self,
        profile: DoctorProfile,
        new_changes: dict[str, Any],
        user_id: UUID,
        *,
        moderation_comment: str | None | _UnsetType = _UNSET,
    ) -> tuple[bool, str | None]:
        """Merge into pending draft or create one. Returns (created_new, public_photo_url if photo_url in new_changes)."""
        if not new_changes:
            raise AppValidationError("Нет полей для отправки на модерацию")

        new_changes = {
            k: self._to_json_change_value(v) for k, v in new_changes.items()
        }

        existing = await self._get_pending_draft(profile.id)
        new_photo_public: str | None = None
        if "photo_url" in new_changes:
            new_photo_public = file_service.build_media_url(str(new_changes["photo_url"]))

        if existing:
            merged = dict(existing.changes)
            merged.update(new_changes)
            existing.changes = merged
            field_keys = list(merged.keys())
            existing.changed_fields = sorted(
                set(existing.changed_fields or []) | set(field_keys)
            )
            flag_modified(existing, "changes")
            flag_modified(existing, "changed_fields")
            if moderation_comment is not _UNSET:
                existing.moderation_comment = moderation_comment
            await self.db.commit()
            return False, new_photo_public

        mc_row = None if moderation_comment is _UNSET else moderation_comment
        draft = DoctorProfileChange(
            doctor_profile_id=profile.id,
            changes=new_changes,
            changed_fields=list(new_changes.keys()),
            status=ChangeStatus.PENDING,
            moderation_comment=mc_row,
        )
        self.db.add(draft)
        await self.db.commit()

        full_name = (
            f"{profile.first_name or ''} {profile.last_name or ''}".strip() or str(user_id)
        )
        from app.tasks.telegram_tasks import notify_admin_new_draft

        await notify_admin_new_draft.kiq(str(user_id), full_name)
        return True, new_photo_public

    async def get_public(self, user_id: UUID) -> dict[str, Any]:
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
            latest_result = await self.db.execute(
                select(DoctorProfileChange)
                .where(DoctorProfileChange.doctor_profile_id == profile.id)
                .order_by(
                    desc(
                        func.coalesce(
                            DoctorProfileChange.reviewed_at,
                            DoctorProfileChange.submitted_at,
                        )
                    )
                )
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
            "specialization": profile.specialization,
            "pending_draft": draft_data,
        }

    async def update_public(self, user_id: UUID, data: dict[str, Any]) -> None:
        """Merge into pending draft or create one (как POST /public/submit, тело JSON)."""
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        moderation_comment: str | None | _UnsetType = _UNSET
        if "moderation_comment" in data:
            moderation_comment = data.pop("moderation_comment")

        if not data:
            if moderation_comment is _UNSET:
                raise NotFoundError("No fields to update")
            existing = await self._get_pending_draft(profile.id)
            if not existing:
                raise AppValidationError(
                    "Нет заявки на модерацию: сначала отправьте изменения профиля",
                )
            existing.moderation_comment = moderation_comment
            await self.db.commit()
            return

        try:
            validated = PublicProfileUpdate.model_validate(data)
        except ValidationError as e:
            raise AppValidationError(
                "Ошибка валидации полей профиля",
                details={"errors": e.errors()},
            ) from e

        changes = validated.model_dump(mode="json", exclude_none=True)
        changes.pop("moderation_comment", None)

        if not changes:
            if moderation_comment is _UNSET:
                raise NotFoundError("No fields to update")
            existing = await self._get_pending_draft(profile.id)
            if not existing:
                raise AppValidationError(
                    "Нет заявки на модерацию: сначала отправьте изменения профиля",
                )
            existing.moderation_comment = moderation_comment
            await self.db.commit()
            return

        await self._upsert_public_draft(
            profile, changes, user_id, moderation_comment=moderation_comment
        )

    async def upload_photo(self, user_id: UUID, upload: UploadFile) -> dict[str, Any]:
        """Upload photo to S3 and merge/create pending draft."""
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

        _, new_public = await self._upsert_public_draft(
            profile,
            {"photo_url": main_key},
            user_id,
        )
        return {
            "photo_url": new_public or "",
            "pending_moderation": True,
        }

    async def submit_public_profile(
        self,
        user_id: UUID,
        *,
        photo: UploadFile | None,
        bio: str | None = None,
        public_email: str | None = None,
        public_phone: str | None = None,
        city_id: str | None = None,
        clinic_name: str | None = None,
        academic_degree: str | None = None,
        specialization: str | None = None,
        moderation_comment: str | None = None,
    ) -> dict[str, Any]:
        """Multipart: optional photo + optional text fields; one merged pending draft."""
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")

        def _form_nonempty_str(name: str, v: str | None) -> None:
            if v is None:
                return
            s = v.strip()
            if not s:
                return
            raw[name] = s

        raw: dict[str, Any] = {}
        _form_nonempty_str("bio", bio)
        _form_nonempty_str("public_email", public_email)
        if public_phone is not None:
            s = public_phone.strip()
            if s:
                raw["public_phone"] = s
        if city_id is not None and str(city_id).strip():
            try:
                raw["city_id"] = UUID(str(city_id).strip())
            except (ValueError, AttributeError) as e:
                raise AppValidationError("Некорректный city_id (ожидается UUID)") from e
        _form_nonempty_str("clinic_name", clinic_name)
        _form_nonempty_str("academic_degree", academic_degree)
        _form_nonempty_str("specialization", specialization)

        try:
            validated = PublicProfileUpdate.model_validate(raw)
        except ValidationError as e:
            raise AppValidationError(
                "Ошибка валидации полей профиля",
                details={"errors": e.errors()},
            ) from e

        text_changes = validated.model_dump(mode="json", exclude_none=True)
        text_changes.pop("moderation_comment", None)

        has_photo = (
            photo is not None
            and getattr(photo, "filename", None)
            and str(photo.filename).strip() != ""
        )

        if not text_changes and not has_photo:
            raise AppValidationError(
                "Укажите хотя бы одно поле или загрузите фото профиля",
            )

        photo_key: str | None = None
        if has_photo:
            main_key, _thumb = await file_service.upload_image_with_thumbnail(
                file=photo,  # type: ignore[arg-type]
                path=f"doctors/{user_id}/photo",
                max_size_mb=5,
            )
            photo_key = main_key

        merged = dict(text_changes)
        if photo_key is not None:
            merged["photo_url"] = photo_key

        mc: str | None | _UnsetType = _UNSET
        if moderation_comment is not None:
            mc = moderation_comment.strip() or None

        _, preview = await self._upsert_public_draft(
            profile,
            merged,
            user_id,
            moderation_comment=mc,
        )

        return {
            "message": "Изменения отправлены на модерацию",
            "pending_moderation": True,
            "photo_url": preview or "",
        }
