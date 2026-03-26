"""XLSX export: subscriptions and plans."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import asc, case, func, nulls_last, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Plan, Subscription
from app.models.users import User
from app.services.exports.export_errors import ExportTooLargeError
from app.services.exports.limits import MAX_EXPORT_ROWS
from app.services.exports.msk import format_date_msk, format_dt_msk, msk_range_to_utc_exclusive_end
from app.services.exports.translations import ru_plan_type, ru_subscription_status
from app.services.exports.xlsx_base import (
    apply_autofilter,
    cell_value,
    new_workbook,
    workbook_to_bytes,
    write_header_row,
)


def _subscription_where(
    *,
    date_from: date | None,
    date_to: date | None,
    status_list: list[str] | None,
    plan_ids: list[UUID] | None,
    plan_types: list[str] | None,
    is_first_year: bool | None,
    active_on: date | None,
    user_id: UUID | None,
) -> list[Any]:
    conds: list[Any] = []
    if date_from is not None and date_to is not None:
        lo, hi = msk_range_to_utc_exclusive_end(date_from, date_to)
        conds.append(Subscription.created_at >= lo)
        conds.append(Subscription.created_at < hi)
    if status_list:
        conds.append(Subscription.status.in_(status_list))
    if plan_ids:
        conds.append(Subscription.plan_id.in_(plan_ids))
    if plan_types:
        conds.append(Plan.plan_type.in_(plan_types))
    if is_first_year is not None:
        conds.append(Subscription.is_first_year.is_(is_first_year))
    if user_id:
        conds.append(Subscription.user_id == user_id)
    if active_on is not None:
        day_lo, day_hi = msk_range_to_utc_exclusive_end(active_on, active_on)
        conds.append(Subscription.starts_at.isnot(None))
        conds.append(Subscription.starts_at < day_hi)
        conds.append(
            or_(Subscription.ends_at.is_(None), Subscription.ends_at >= day_lo)
        )
    return conds


def _payment_aggregates(
    payments: list[Payment],
) -> dict[UUID, tuple[int, Decimal, Any, str | None]]:
    """subscription_id -> (count, sum succeeded, last paid_at, last payment status)."""
    by_sub: dict[UUID, list[Payment]] = defaultdict(list)
    for p in payments:
        if p.subscription_id:
            by_sub[p.subscription_id].append(p)
    out: dict[UUID, tuple[int, Decimal, Any, str | None]] = {}
    for sid, plist in by_sub.items():
        succeeded = [p for p in plist if str(p.status) == "succeeded"]
        total_amt = sum(Decimal(str(p.amount)) for p in succeeded)
        with_paid_at = [p for p in plist if p.paid_at is not None]
        last_p = max(with_paid_at, key=lambda p: p.paid_at) if with_paid_at else None
        last_status = str(last_p.status) if last_p else None
        last_paid = last_p.paid_at if last_p else None
        out[sid] = (len(plist), total_amt, last_paid, last_status)
    return out


async def build_subscriptions_xlsx(
    db: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    status_list: list[str] | None = None,
    plan_ids: list[UUID] | None = None,
    plan_types: list[str] | None = None,
    is_first_year: bool | None = None,
    active_on: date | None = None,
    user_id: UUID | None = None,
) -> bytes:
    conds = _subscription_where(
        date_from=date_from,
        date_to=date_to,
        status_list=status_list,
        plan_ids=plan_ids,
        plan_types=plan_types,
        is_first_year=is_first_year,
        active_on=active_on,
        user_id=user_id,
    )

    base = Subscription.__table__.join(Plan.__table__, Subscription.plan_id == Plan.id).join(
        User.__table__, Subscription.user_id == User.id
    ).outerjoin(DoctorProfile.__table__, DoctorProfile.user_id == User.id)

    cnt_q = select(func.count(Subscription.id)).select_from(base)
    if conds:
        cnt_q = cnt_q.where(*conds)
    total = (await db.execute(cnt_q)).scalar() or 0
    if total > MAX_EXPORT_ROWS:
        raise ExportTooLargeError(total)

    status_rank = case(
        (Subscription.status == "active", 0),
        (Subscription.status == "expired", 1),
        (Subscription.status == "pending_payment", 2),
        (Subscription.status == "cancelled", 3),
        else_=4,
    )

    stmt = (
        select(Subscription, Plan, User, DoctorProfile)
        .join(Plan, Subscription.plan_id == Plan.id)
        .join(User, Subscription.user_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
    )
    if conds:
        stmt = stmt.where(*conds)
    stmt = stmt.order_by(
        status_rank,
        nulls_last(asc(Subscription.ends_at)),
    )

    result = await db.execute(stmt)
    rows_orm = result.all()

    sub_ids = [row[0].id for row in rows_orm]
    pay_map: dict[UUID, tuple[int, Decimal, Any, str | None]] = {}
    if sub_ids:
        pq = select(Payment).where(Payment.subscription_id.in_(sub_ids))
        pays = (await db.execute(pq)).scalars().all()
        pay_map = _payment_aggregates(list(pays))

    headers = [
        "ID подписки",
        "Статус (EN)",
        "Статус (RU)",
        "Дата начала",
        "Дата окончания",
        "Первый год / Продление",
        "Дата создания записи",
        "Название плана",
        "Код плана",
        "Цена плана (руб.)",
        "Тип плана (EN)",
        "Тип плана (RU)",
        "Длительность (мес.)",
        "Email",
        "Фамилия",
        "Имя",
        "Отчество",
        "Телефон",
        "Статус врача",
        "Кол-во платежей по подписке",
        "Сумма оплачено (руб.)",
        "Последний платёж: дата",
        "Последний платёж: статус (EN)",
    ]

    wb, ws = new_workbook("Подписки")
    write_header_row(ws, 1, headers)

    r = 2
    for row in rows_orm:
        sub, plan, u, dp = row
        agg = pay_map.get(sub.id, (0, Decimal("0"), None, None))
        pcnt, psum, last_paid, last_st = agg
        first_label = "Первый год" if sub.is_first_year else "Продление"
        line = [
            str(sub.id),
            str(sub.status),
            ru_subscription_status(str(sub.status)),
            format_date_msk(sub.starts_at) if sub.starts_at else None,
            format_date_msk(sub.ends_at) if sub.ends_at else None,
            first_label,
            format_dt_msk(sub.created_at),
            plan.name,
            plan.code,
            float(plan.price),
            str(plan.plan_type),
            ru_plan_type(str(plan.plan_type)),
            plan.duration_months,
            u.email,
            cell_value(dp.last_name if dp else None),
            cell_value(dp.first_name if dp else None),
            cell_value(dp.middle_name if dp else None),
            cell_value(dp.phone if dp else None),
            str(dp.status) if dp else None,
            pcnt,
            float(psum) if psum else None,
            format_dt_msk(last_paid) if last_paid else None,
            last_st,
        ]
        for c_idx, val in enumerate(line, start=1):
            ws.cell(row=r, column=c_idx, value=val)
        r += 1

    last_data_row = r - 1
    if last_data_row >= 1:
        apply_autofilter(ws, len(headers), last_data_row)

    return workbook_to_bytes(wb)
