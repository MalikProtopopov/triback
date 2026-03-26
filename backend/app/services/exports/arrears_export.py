"""XLSX export: membership arrears."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arrears import MembershipArrear
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment
from app.models.users import User
from app.services.exports.export_errors import ExportTooLargeError
from app.services.exports.limits import MAX_EXPORT_ROWS
from app.services.exports.msk import format_dt_msk, msk_range_to_utc_exclusive_end
from app.services.exports.translations import ru_arrear_status
from app.services.exports.xlsx_base import (
    apply_autofilter,
    bold_font,
    cell_value,
    new_workbook,
    workbook_to_bytes,
    write_header_row,
)


def _arrears_where(
    *,
    date_from: date | None,
    date_to: date | None,
    status_list: list[str] | None,
    years: list[int] | None,
    user_id: UUID | None,
) -> list[Any]:
    conds: list[Any] = []
    if date_from is not None and date_to is not None:
        lo, hi = msk_range_to_utc_exclusive_end(date_from, date_to)
        conds.append(MembershipArrear.created_at >= lo)
        conds.append(MembershipArrear.created_at < hi)
    if status_list:
        conds.append(MembershipArrear.status.in_(status_list))
    if years:
        conds.append(MembershipArrear.year.in_(years))
    if user_id:
        conds.append(MembershipArrear.user_id == user_id)
    return conds


def _arrears_select() -> Select[Any]:
    return (
        select(MembershipArrear, User, DoctorProfile, Payment)
        .join(User, MembershipArrear.user_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .outerjoin(Payment, Payment.id == MembershipArrear.payment_id)
    )


async def build_arrears_xlsx(
    db: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    status_list: list[str] | None = None,
    years: list[int] | None = None,
    user_id: UUID | None = None,
) -> bytes:
    conds = _arrears_where(
        date_from=date_from,
        date_to=date_to,
        status_list=status_list,
        years=years,
        user_id=user_id,
    )

    cnt_q = select(func.count(MembershipArrear.id)).select_from(MembershipArrear)
    if conds:
        cnt_q = cnt_q.where(*conds)
    total = (await db.execute(cnt_q)).scalar() or 0
    if total > MAX_EXPORT_ROWS:
        raise ExportTooLargeError(total)

    order_open_first = case(
        (MembershipArrear.status == "open", 0),
        else_=1,
    )
    stmt = _arrears_select()
    if conds:
        stmt = stmt.where(*conds)
    stmt = stmt.order_by(order_open_first, MembershipArrear.year.desc())

    result = await db.execute(stmt)
    rows_orm = result.all()

    headers = [
        "ID задолженности",
        "Год задолженности",
        "Сумма (руб.)",
        "Статус (EN)",
        "Статус (RU)",
        "Основание",
        "Внутренняя заметка",
        "Источник",
        "Дата создания",
        "Дата оплаты",
        "Дата списания",
        "Причина списания",
        "Email должника",
        "Фамилия",
        "Имя",
        "Отчество",
        "Телефон",
        "ID закрывающего платежа",
        "Сумма оплаченного платежа (руб.)",
        "Дата оплаты (платёж)",
    ]

    wb, ws = new_workbook("Задолженности")
    write_header_row(ws, 1, headers)

    open_total = Decimal("0")
    r = 2
    for row in rows_orm:
        a, u, dp, pay = row
        if str(a.status) == "open":
            open_total += Decimal(str(a.amount))

        line = [
            str(a.id),
            a.year,
            float(a.amount),
            str(a.status),
            ru_arrear_status(str(a.status)),
            cell_value(a.description),
            cell_value(a.admin_note),
            str(a.source),
            format_dt_msk(a.created_at),
            format_dt_msk(a.paid_at),
            format_dt_msk(a.waived_at),
            cell_value(a.waive_reason),
            u.email,
            cell_value(dp.last_name if dp else None),
            cell_value(dp.first_name if dp else None),
            cell_value(dp.middle_name if dp else None),
            cell_value(dp.phone if dp else None),
            cell_value(str(a.payment_id) if a.payment_id else None),
            float(pay.amount) if pay else None,
            format_dt_msk(pay.paid_at) if pay else None,
        ]
        for c_idx, val in enumerate(line, start=1):
            ws.cell(row=r, column=c_idx, value=val)
        r += 1

    last_data_row = r - 1
    if last_data_row >= 1:
        apply_autofilter(ws, len(headers), last_data_row)

    if last_data_row >= 1 and open_total > 0:
        r += 1
        ws.cell(row=r, column=1, value="Итого (открытые)").font = bold_font()
        ws.cell(row=r, column=3, value=float(open_total)).font = bold_font()

    return workbook_to_bytes(wb)
