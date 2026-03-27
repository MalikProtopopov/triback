"""Doctor CRUD — create, list, get detail."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.enums import ChangeStatus, SubscriptionStatus
from app.core.exceptions import NotFoundError
from app.models.profiles import (
    DoctorProfile,
    DoctorProfileChange,
    ModerationHistory,
)
from app.models.subscriptions import Payment, Subscription
from app.models.users import TelegramBinding, User
from app.schemas.doctor_admin import (
    DoctorDetailResponse,
    DoctorListItemResponse,
    DocumentNested,
    ModerationHistoryNested,
    PendingDraftNested,
)
from app.schemas.shared import (
    SubscriptionNested,
    block_to_nested,
    city_to_nested,
    payment_to_nested,
    subscription_to_nested,
)
from app.services import file_service
from app.services.content_block_service import list_blocks_for_entity

logger = structlog.get_logger(__name__)

class DoctorAdminRead:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _latest_subscription_nested(self, user_id: UUID) -> SubscriptionNested | None:
        result = await self.db.execute(
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub = result.scalar_one_or_none()
        return subscription_to_nested(sub)

    async def list_doctors(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        subscription_status: str | None = None,
        board_role: list[str] | None = None,
        city_id: UUID | None = None,
        has_data_changed: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        base = (
            select(DoctorProfile)
            .join(User, DoctorProfile.user_id == User.id)
            .options(joinedload(DoctorProfile.user), joinedload(DoctorProfile.city))
        )

        count_q = (
            select(func.count(DoctorProfile.id))
            .join(User, DoctorProfile.user_id == User.id)
        )

        filters: list[Any] = []

        if status:
            filters.append(DoctorProfile.status == status)
        if board_role and len(board_role) > 0:
            filters.append(DoctorProfile.board_role.in_(board_role))
        if city_id:
            filters.append(DoctorProfile.city_id == city_id)
        if search and len(search) >= 2:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    DoctorProfile.last_name.ilike(pattern),
                    DoctorProfile.first_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )
        if has_data_changed is True:
            pending_exists = exists(
                select(DoctorProfileChange.id).where(
                    and_(
                        DoctorProfileChange.doctor_profile_id == DoctorProfile.id,
                        DoctorProfileChange.status == ChangeStatus.PENDING,
                    )
                )
            )
            filters.append(pending_exists)

        need_sub_join = subscription_status is not None or sort_by == "subscription_ends_at"

        if need_sub_join:
            latest_sub = (
                select(
                    Subscription.user_id,
                    Subscription.status.label("sub_status"),
                    Subscription.ends_at.label("sub_ends_at"),
                    func.row_number()
                    .over(partition_by=Subscription.user_id, order_by=Subscription.created_at.desc())
                    .label("rn"),
                )
                .subquery("latest_sub")
            )
            sub_sq = (
                select(
                    latest_sub.c.user_id,
                    latest_sub.c.sub_status,
                    latest_sub.c.sub_ends_at,
                )
                .where(latest_sub.c.rn == 1)
                .subquery("sub_sq")
            )
            base = base.outerjoin(sub_sq, DoctorProfile.user_id == sub_sq.c.user_id)
            count_q = count_q.outerjoin(sub_sq, DoctorProfile.user_id == sub_sq.c.user_id)

            if subscription_status == "expiring_soon":
                now = datetime.now(UTC)
                filters.append(
                    and_(
                        sub_sq.c.sub_status == SubscriptionStatus.ACTIVE,
                        sub_sq.c.sub_ends_at.between(now, now + timedelta(days=7)),
                    )
                )
            elif subscription_status == "never":
                filters.append(sub_sq.c.sub_status.is_(None))
            elif subscription_status:
                filters.append(sub_sq.c.sub_status == subscription_status)

        if filters:
            base = base.where(and_(*filters))
            count_q = count_q.where(and_(*filters))

        total = (await self.db.execute(count_q)).scalar() or 0

        base = self._apply_sort(base, sort_by, sort_order, need_sub_join)
        base = base.offset(offset).limit(limit)

        rows = (await self.db.execute(base)).unique().scalars().all()

        user_ids = [dp.user_id for dp in rows]
        profile_ids = [dp.id for dp in rows]

        sub_map: dict[UUID, SubscriptionNested] = {}
        if user_ids:
            sub_q = (
                select(Subscription)
                .options(joinedload(Subscription.plan))
                .where(Subscription.user_id.in_(user_ids))
                .order_by(Subscription.user_id, Subscription.created_at.desc())
            )
            sub_rows = (await self.db.execute(sub_q)).unique().scalars().all()
            for s in sub_rows:
                if s.user_id not in sub_map:
                    nested = subscription_to_nested(s)
                    if nested:
                        sub_map[s.user_id] = nested

        tg_map: dict[UUID, TelegramBinding] = {}
        if user_ids:
            tg_rows = (
                await self.db.execute(
                    select(TelegramBinding).where(TelegramBinding.user_id.in_(user_ids))
                )
            ).scalars().all()
            for tb in tg_rows:
                tg_map[tb.user_id] = tb

        pending_set: set[UUID] = set()
        photo_draft_set: set[UUID] = set()
        if profile_ids:
            pending_rows = (
                await self.db.execute(
                    select(
                        DoctorProfileChange.doctor_profile_id,
                        DoctorProfileChange.changed_fields,
                    ).where(
                        DoctorProfileChange.doctor_profile_id.in_(profile_ids),
                        DoctorProfileChange.status == ChangeStatus.PENDING,
                    )
                )
            ).all()
            for row in pending_rows:
                profile_id = row[0]
                changed_fields = row[1] or []
                pending_set.add(profile_id)
                if "photo_url" in changed_fields:
                    photo_draft_set.add(profile_id)

        items: list[DoctorListItemResponse] = []
        for dp in rows:
            items.append(
                DoctorListItemResponse(
                    id=dp.id,
                    user_id=dp.user_id,
                    email=dp.user.email,
                    first_name=dp.first_name,
                    last_name=dp.last_name,
                    middle_name=dp.middle_name,
                    phone=dp.phone,
                    city=city_to_nested(dp.city),
                    specialization=dp.specialization,
                    moderation_status=dp.status,
                    has_medical_diploma=dp.has_medical_diploma,
                    subscription=sub_map.get(dp.user_id),
                    has_pending_changes=dp.id in pending_set,
                    has_photo_in_draft=dp.id in photo_draft_set,
                    telegram_linked=dp.user_id in tg_map,
                    tg_username=tg_map[dp.user_id].tg_username if dp.user_id in tg_map else None,
                    board_role=dp.board_role,
                    created_at=dp.created_at,
                )
            )

        return {"data": items, "total": total, "limit": limit, "offset": offset}

    def _apply_sort(
        self, q: Select, sort_by: str, sort_order: str, has_sub_join: bool  # type: ignore[type-arg]
    ) -> Select:  # type: ignore[type-arg]
        col: Any
        if sort_by == "last_name":
            col = DoctorProfile.last_name
        elif sort_by == "subscription_ends_at" and has_sub_join:
            col = func.coalesce(
                select(Subscription.ends_at)
                .where(Subscription.user_id == DoctorProfile.user_id)
                .order_by(Subscription.created_at.desc())
                .limit(1)
                .correlate(DoctorProfile)
                .scalar_subquery(),
                datetime.min,
            )
        else:
            col = DoctorProfile.created_at

        return q.order_by(col.desc() if sort_order == "desc" else col.asc())

    async def get_doctor(self, profile_id: UUID) -> DoctorDetailResponse:
        result = await self.db.execute(
            select(DoctorProfile)
            .options(
                joinedload(DoctorProfile.user),
                joinedload(DoctorProfile.city),
                selectinload(DoctorProfile.documents),
                selectinload(DoctorProfile.profile_changes),
            )
            .where(DoctorProfile.id == profile_id)
        )
        dp = result.unique().scalar_one_or_none()
        if not dp:
            raise NotFoundError("Doctor profile not found")

        sub_info = await self._latest_subscription_nested(dp.user_id)

        payments_result = await self.db.execute(
            select(Payment)
            .where(Payment.user_id == dp.user_id)
            .order_by(Payment.created_at.desc())
            .limit(20)
        )
        payments_rows = payments_result.scalars().all()

        pending_draft: PendingDraftNested | None = None
        for pc in dp.profile_changes:
            if pc.status == ChangeStatus.PENDING:
                pending_draft = PendingDraftNested(
                    id=pc.id,
                    changes=pc.changes,
                    changed_fields=pc.changed_fields,
                    status=pc.status,
                    moderation_comment=pc.moderation_comment,
                    submitted_at=pc.submitted_at,
                    rejection_reason=pc.rejection_reason,
                )
                break

        mod_history_result = await self.db.execute(
            select(ModerationHistory)
            .where(
                and_(
                    ModerationHistory.entity_type == "doctor_profile",
                    ModerationHistory.entity_id == profile_id,
                )
            )
            .order_by(ModerationHistory.created_at.desc())
        )
        mod_rows = mod_history_result.scalars().all()

        admin_ids = {mh.admin_id for mh in mod_rows if mh.admin_id}
        admin_email_map: dict[UUID, str] = {}
        if admin_ids:
            admin_q = await self.db.execute(
                select(User.id, User.email).where(User.id.in_(admin_ids))
            )
            for row in admin_q.all():
                admin_email_map[row.id] = row.email

        mod_items = [
            ModerationHistoryNested(
                id=mh.id,
                admin_email=admin_email_map.get(mh.admin_id),
                action=mh.action,
                comment=mh.comment,
                created_at=mh.created_at,
            )
            for mh in mod_rows
        ]

        blocks = await list_blocks_for_entity(self.db, "doctor_profile", profile_id)

        tg_binding = (
            await self.db.execute(
                select(TelegramBinding).where(TelegramBinding.user_id == dp.user_id)
            )
        ).scalar_one_or_none()

        return DoctorDetailResponse(
            id=dp.id,
            user_id=dp.user_id,
            email=dp.user.email,
            first_name=dp.first_name,
            last_name=dp.last_name,
            middle_name=dp.middle_name,
            phone=dp.phone,
            passport_data=dp.passport_data,
            city=city_to_nested(dp.city),
            clinic_name=dp.clinic_name,
            position=dp.position,
            specialization=dp.specialization,
            academic_degree=dp.academic_degree,
            bio=dp.bio,
            public_email=dp.public_email,
            public_phone=dp.public_phone,
            photo_url=file_service.build_media_url(dp.photo_url),
            moderation_status=dp.status,
            has_medical_diploma=dp.has_medical_diploma,
            diploma_photo_url=file_service.build_media_url(dp.diploma_photo_url),
            slug=dp.slug,
            documents=[
                DocumentNested(
                    id=d.id,
                    document_type=d.document_type,
                    original_filename=d.original_filename,
                    file_url=file_service.build_media_url(d.file_url),
                    file_size=d.file_size,
                    mime_type=d.mime_type,
                    uploaded_at=d.uploaded_at,
                )
                for d in dp.documents
            ],
            subscription=sub_info,
            payments=[payment_to_nested(p) for p in payments_rows],
            pending_draft=pending_draft,
            moderation_history=mod_items,
            content_blocks=[block_to_nested(b) for b in blocks],
            telegram_linked=tg_binding is not None,
            tg_username=tg_binding.tg_username if tg_binding else None,
            board_role=dp.board_role,
            created_at=dp.created_at,
            entry_fee_exempt=bool(dp.entry_fee_exempt),
            membership_excluded_at=dp.membership_excluded_at,
        )
