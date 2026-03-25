"""Admin dashboard router — aggregated metrics."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.models.arrears import MembershipArrear
from app.models.events import Event
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Subscription
from app.models.users import User

router = APIRouter(prefix="/admin")


class DashboardResponse(BaseModel):
    total_users: int
    total_doctors: int
    active_doctors: int
    pending_review_doctors: int
    active_subscriptions: int
    expiring_30d: int
    payment_total_month: float
    payment_total_year: float
    upcoming_events: int
    moderation_queue: int
    arrears_open_total: float
    arrears_open_count: int
    arrears_paid_total: float
    arrears_paid_count: int
    arrears_waived_total: float
    arrears_waived_count: int


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Сводная статистика",
    responses=error_responses(401, 403),
)
async def get_dashboard(
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Агрегированные метрики платформы: пользователи, подписки, платежи,
    мероприятия, очередь модерации.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    thirty_days = now + timedelta(days=30)

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    total_doctors = (
        await db.execute(select(func.count(DoctorProfile.id)))
    ).scalar() or 0

    active_doctors = (
        await db.execute(
            select(func.count(DoctorProfile.id)).where(DoctorProfile.status == "active")
        )
    ).scalar() or 0

    pending_review = (
        await db.execute(
            select(func.count(DoctorProfile.id)).where(
                DoctorProfile.status == "pending_review"
            )
        )
    ).scalar() or 0

    active_subs = (
        await db.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )
    ).scalar() or 0

    expiring_30d = (
        await db.execute(
            select(func.count(Subscription.id)).where(
                and_(
                    Subscription.status == "active",
                    Subscription.ends_at <= thirty_days,
                    Subscription.ends_at >= now,
                )
            )
        )
    ).scalar() or 0

    payment_month = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                and_(
                    Payment.status == "succeeded",
                    Payment.paid_at >= month_start,
                )
            )
        )
    ).scalar() or 0

    payment_year = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                and_(
                    Payment.status == "succeeded",
                    Payment.paid_at >= year_start,
                )
            )
        )
    ).scalar() or 0

    upcoming_events = (
        await db.execute(
            select(func.count(Event.id)).where(
                and_(
                    Event.status == "upcoming",
                    Event.event_date >= now,
                )
            )
        )
    ).scalar() or 0

    moderation_queue = pending_review

    arrears_open_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(MembershipArrear.amount), 0),
                func.count(MembershipArrear.id),
            ).where(MembershipArrear.status == "open")
        )
    ).one()
    arrears_paid_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(MembershipArrear.amount), 0),
                func.count(MembershipArrear.id),
            ).where(MembershipArrear.status == "paid")
        )
    ).one()
    arrears_waived_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(MembershipArrear.amount), 0),
                func.count(MembershipArrear.id),
            ).where(MembershipArrear.status == "waived")
        )
    ).one()

    return {
        "total_users": total_users,
        "total_doctors": total_doctors,
        "active_doctors": active_doctors,
        "pending_review_doctors": pending_review,
        "active_subscriptions": active_subs,
        "expiring_30d": expiring_30d,
        "payment_total_month": float(payment_month),
        "payment_total_year": float(payment_year),
        "upcoming_events": upcoming_events,
        "moderation_queue": moderation_queue,
        "arrears_open_total": float(arrears_open_row[0] or 0),
        "arrears_open_count": int(arrears_open_row[1] or 0),
        "arrears_paid_total": float(arrears_paid_row[0] or 0),
        "arrears_paid_count": int(arrears_paid_row[1] or 0),
        "arrears_waived_total": float(arrears_waived_row[0] or 0),
        "arrears_waived_count": int(arrears_waived_row[1] or 0),
    }
