"""Doctor moderation — approve/reject profiles and drafts, toggle visibility."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChangeStatus, DoctorStatus, ModerationAction, SubscriptionStatus
from app.core.exceptions import NotFoundError
from app.core.utils import generate_unique_slug
from app.models.profiles import DoctorProfile, DoctorProfileChange, ModerationHistory
from app.models.subscriptions import Subscription
from app.models.users import User
from app.tasks.email_tasks import (
    send_draft_result_notification,
    send_moderation_result_notification,
)


class DoctorModerationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_profile_or_404(self, profile_id: UUID) -> DoctorProfile:
        result = await self.db.execute(
            select(DoctorProfile).where(DoctorProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError("Doctor profile not found")
        return profile

    async def moderate(
        self,
        profile_id: UUID,
        admin_id: UUID,
        action: str,
        comment: str | None = None,
    ) -> str:
        dp = await self._get_profile_or_404(profile_id)

        new_status = DoctorStatus.APPROVED if action == ModerationAction.APPROVE else DoctorStatus.REJECTED
        dp.status = new_status

        if action == "approve" and not dp.slug:
            dp.slug = await generate_unique_slug(
                self.db, DoctorProfile, f"{dp.last_name} {dp.first_name}"
            )

        self.db.add(
            ModerationHistory(
                admin_id=admin_id,
                entity_type="doctor_profile",
                entity_id=profile_id,
                action=action,
                comment=comment,
            )
        )

        await self.db.flush()

        has_active_subscription = False
        if new_status == DoctorStatus.APPROVED:
            sub_q = await self.db.execute(
                select(Subscription.id).where(
                    Subscription.user_id == dp.user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    or_(
                        Subscription.ends_at.is_(None),
                        Subscription.ends_at > datetime.now(UTC),
                    ),
                ).limit(1)
            )
            has_active_subscription = sub_q.scalar_one_or_none() is not None

        user = await self.db.get(User, dp.user_id)
        if user:
            await send_moderation_result_notification.kiq(
                user.email, new_status, comment,
                has_active_subscription=has_active_subscription if new_status == DoctorStatus.APPROVED else None,
            )
            from app.tasks.telegram_tasks import notify_user_moderation_result

            await notify_user_moderation_result.kiq(str(dp.user_id), new_status, comment)

        await self.db.commit()
        return new_status

    async def approve_draft(
        self,
        profile_id: UUID,
        admin_id: UUID,
        action: str,
        rejection_reason: str | None = None,
    ) -> str:
        dp = await self._get_profile_or_404(profile_id)

        result = await self.db.execute(
            select(DoctorProfileChange).where(
                and_(
                    DoctorProfileChange.doctor_profile_id == profile_id,
                    DoctorProfileChange.status == ChangeStatus.PENDING,
                )
            )
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise NotFoundError("No pending draft found")

        now = datetime.now(UTC)

        if action == "approve":
            for key, value in draft.changes.items():
                if hasattr(dp, key):
                    setattr(dp, key, value)
            draft.status = ChangeStatus.APPROVED
            draft.reviewed_at = now
            draft.reviewed_by = admin_id
            msg = "Changes approved and applied"
        else:
            draft.status = ChangeStatus.REJECTED
            draft.reviewed_at = now
            draft.reviewed_by = admin_id
            draft.rejection_reason = rejection_reason
            msg = "Changes rejected"

        self.db.add(
            ModerationHistory(
                admin_id=admin_id,
                entity_type="doctor_profile",
                entity_id=profile_id,
                action=f"draft_{action}",
                comment=rejection_reason if action == "reject" else None,
            )
        )
        await self.db.flush()

        user = await self.db.get(User, dp.user_id)
        if user:
            email_status = ChangeStatus.APPROVED if action == ModerationAction.APPROVE else ChangeStatus.REJECTED
            await send_draft_result_notification.kiq(
                user.email, email_status, rejection_reason
            )
            from app.tasks.telegram_tasks import notify_user_draft_result

            await notify_user_draft_result.kiq(str(dp.user_id), action, rejection_reason)

        await self.db.commit()
        return msg

    async def toggle_active(self, profile_id: UUID, admin_id: UUID, is_public: bool) -> bool:
        dp = await self._get_profile_or_404(profile_id)

        if is_public:
            dp.status = DoctorStatus.ACTIVE
        else:
            dp.status = DoctorStatus.DEACTIVATED

        self.db.add(
            ModerationHistory(
                admin_id=admin_id,
                entity_type="doctor_profile",
                entity_id=profile_id,
                action="activate" if is_public else "deactivate",
            )
        )
        await self.db.commit()
        return is_public
