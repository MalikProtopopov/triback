"""Public doctor catalog — list and detail for guest access."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.enums import DoctorStatus, SubscriptionStatus
from app.core.exceptions import NotFoundError
from app.models.cities import City
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Subscription
from app.schemas.public import DoctorPublicDetailResponse, DoctorPublicListItem, SeoNested
from app.schemas.shared import ContentBlockPublicNested
from app.services import file_service
from app.services.content_block_service import list_blocks_for_entity
from app.services.membership_arrears_service import (
    arrears_block_enabled,
    correlated_open_arrears_exist,
    load_site_settings_dict,
)


def _has_active_subscription() -> Any:
    return (
        select(Subscription.id)
        .where(
            Subscription.user_id == DoctorProfile.user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            or_(
                Subscription.ends_at.is_(None),
                Subscription.ends_at > func.now(),
            ),
        )
        .correlate(DoctorProfile)
        .exists()
    )


class DoctorCatalogService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_doctors(
        self,
        *,
        limit: int = 12,
        offset: int = 0,
        city_id: UUID | None = None,
        city_slug: str | None = None,
        specialization: str | None = None,
        board_role: list[str] | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        settings_data = await load_site_settings_dict(self.db)
        block_arrears = arrears_block_enabled(settings_data)
        active_sub = _has_active_subscription()
        visible = (
            and_(active_sub, ~correlated_open_arrears_exist())
            if block_arrears
            else active_sub
        )
        base = (
            select(DoctorProfile)
            .options(joinedload(DoctorProfile.city))
            .where(DoctorProfile.status == DoctorStatus.ACTIVE, visible)
        )
        count_q = select(func.count(DoctorProfile.id)).where(
            DoctorProfile.status == DoctorStatus.ACTIVE, visible
        )

        filters: list[Any] = []

        if city_slug and not city_id:
            city_result = await self.db.execute(
                select(City.id).where(City.slug == city_slug)
            )
            resolved = city_result.scalar_one_or_none()
            if resolved:
                city_id = resolved

        if city_id:
            filters.append(DoctorProfile.city_id == city_id)
        if board_role and len(board_role) > 0:
            filters.append(DoctorProfile.board_role.in_(board_role))
        if specialization:
            filters.append(DoctorProfile.specialization.ilike(f"%{specialization}%"))
        if search and len(search) >= 2:
            pattern = f"%{search}%"
            filters.append(
                or_(DoctorProfile.last_name.ilike(pattern), DoctorProfile.first_name.ilike(pattern))
            )

        if filters:
            base = base.where(and_(*filters))
            count_q = count_q.where(and_(*filters))

        total = (await self.db.execute(count_q)).scalar() or 0

        base = base.order_by(DoctorProfile.last_name, DoctorProfile.first_name)
        base = base.offset(offset).limit(limit)

        rows = (await self.db.execute(base)).unique().scalars().all()
        items = [self._to_list_item(dp) for dp in rows]
        return {"data": items, "total": total, "limit": limit, "offset": offset}

    def _to_list_item(self, dp: DoctorProfile) -> DoctorPublicListItem:
        return DoctorPublicListItem(
            id=dp.id,
            first_name=dp.first_name,
            last_name=dp.last_name,
            middle_name=dp.middle_name,
            city=dp.city.name if dp.city else None,
            clinic_name=dp.clinic_name,
            specialization=dp.specialization,
            academic_degree=dp.academic_degree,
            bio=dp.bio,
            photo_url=file_service.build_media_url(dp.photo_url),
            public_phone=dp.public_phone,
            public_email=dp.public_email,
            slug=dp.slug,
            board_role=dp.board_role,
        )

    async def get_doctor(self, identifier: str) -> DoctorPublicDetailResponse:
        try:
            uid = UUID(identifier)
            id_filter = DoctorProfile.id == uid
        except (ValueError, AttributeError):
            id_filter = DoctorProfile.slug == identifier

        settings_data = await load_site_settings_dict(self.db)
        block_arrears = arrears_block_enabled(settings_data)
        active_sub = _has_active_subscription()
        visible = (
            and_(active_sub, ~correlated_open_arrears_exist())
            if block_arrears
            else active_sub
        )

        result = await self.db.execute(
            select(DoctorProfile)
            .options(joinedload(DoctorProfile.city))
            .where(
                and_(
                    id_filter,
                    DoctorProfile.status == DoctorStatus.ACTIVE,
                    visible,
                )
            )
        )
        dp = result.unique().scalar_one_or_none()
        if not dp:
            raise NotFoundError("Doctor not found")

        city_name = dp.city.name if dp.city else None
        full_name = f"{dp.last_name} {dp.first_name}"
        if dp.middle_name:
            full_name += f" {dp.middle_name}"

        seo = SeoNested(
            title=f"{full_name} — врач-трихолог{f' в г. {city_name}' if city_name else ''} | РОТА",
            description=f"Публичный профиль врача-трихолога {full_name}.{f' {dp.clinic_name}, {city_name}.' if dp.clinic_name and city_name else ''}",
            og_type="profile",
            og_image=file_service.build_media_url(dp.photo_url),
            twitter_card="summary_large_image",
        )

        blocks = await list_blocks_for_entity(self.db, "doctor_profile", dp.id)
        content_blocks = [
            ContentBlockPublicNested(
                id=str(b.id),
                block_type=b.block_type,
                sort_order=b.sort_order,
                title=b.title,
                content=b.content,
                media_url=file_service.build_media_url(b.media_url),
                thumbnail_url=file_service.build_media_url(b.thumbnail_url),
                link_url=b.link_url,
                link_label=b.link_label,
                device_type=b.device_type,
            )
            for b in blocks
        ]

        return DoctorPublicDetailResponse(
            id=dp.id,
            first_name=dp.first_name,
            last_name=dp.last_name,
            middle_name=dp.middle_name,
            city=city_name,
            clinic_name=dp.clinic_name,
            position=dp.position,
            specialization=dp.specialization,
            academic_degree=dp.academic_degree,
            bio=dp.bio,
            photo_url=file_service.build_media_url(dp.photo_url),
            public_phone=dp.public_phone,
            public_email=dp.public_email,
            slug=dp.slug,
            board_role=dp.board_role,
            seo=seo,
            content_blocks=content_blocks,
        )
