"""Colleagues endpoint — active doctors list with contacts for members."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db_session
from app.core.enums import DoctorStatus, SubscriptionStatus
from app.core.exceptions import ForbiddenError
from app.core.openapi import error_responses
from app.core.security import require_role
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Subscription
from app.services import file_service

router = APIRouter(prefix="/colleagues")

DOCTOR = require_role("doctor")


async def _require_active_subscription(db: AsyncSession, user_id: UUID) -> None:
    result = await db.execute(
        select(Subscription.id).where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            or_(
                Subscription.ends_at.is_(None),
                Subscription.ends_at > func.now(),
            ),
        ).limit(1)
    )
    if result.scalar_one_or_none() is None:
        raise ForbiddenError("Доступ только для врачей с активной подпиской")


@router.get(
    "",
    summary="Список коллег",
    description=(
        "Возвращает список врачей с контактными данными для коллег. "
        "Доступен только авторизованным врачам с активной подпиской."
    ),
    responses=error_responses(403),
)
async def list_colleagues(
    db: AsyncSession = Depends(get_db_session),
    payload: dict[str, Any] = DOCTOR,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, min_length=2, max_length=100),
) -> dict[str, Any]:
    user_id = UUID(payload["sub"])
    await _require_active_subscription(db, user_id)

    active_sub_exists = (
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

    base = (
        select(DoctorProfile)
        .options(
            joinedload(DoctorProfile.city),
            joinedload(DoctorProfile.specialization),
        )
        .where(DoctorProfile.status == DoctorStatus.ACTIVE, active_sub_exists)
    )
    count_q = select(func.count(DoctorProfile.id)).where(
        DoctorProfile.status == DoctorStatus.ACTIVE, active_sub_exists
    )

    if search:
        pattern = f"%{search}%"
        name_filter = or_(
            DoctorProfile.last_name.ilike(pattern),
            DoctorProfile.first_name.ilike(pattern),
        )
        base = base.where(name_filter)
        count_q = count_q.where(name_filter)

    total = (await db.execute(count_q)).scalar() or 0
    base = base.order_by(DoctorProfile.last_name, DoctorProfile.first_name)
    base = base.offset(offset).limit(limit)
    rows = (await db.execute(base)).unique().scalars().all()

    items = [
        {
            "id": str(dp.id),
            "first_name": dp.first_name,
            "last_name": dp.last_name,
            "middle_name": dp.middle_name,
            "city": dp.city.name if dp.city else None,
            "specialization": dp.specialization.name if dp.specialization else None,
            "photo_url": file_service.build_media_url(dp.photo_url),
            "public_phone": dp.public_phone,
            "public_email": dp.public_email,
            "colleague_contacts": dp.colleague_contacts,
        }
        for dp in rows
    ]

    return {"data": items, "total": total, "limit": limit, "offset": offset}
