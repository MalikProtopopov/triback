"""XLSX export: event registrations with payment."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.events import Event, EventRegistration, EventTariff
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Receipt
from app.models.users import User
from app.services.exports.export_errors import ExportTooLargeError
from app.services.exports.limits import MAX_EXPORT_ROWS
from app.services.exports.msk import format_date_msk, format_dt_msk, msk_range_to_utc_exclusive_end
from app.services.exports.translations import ru_event_reg_status, ru_payment_status
from app.services.exports.xlsx_base import (
    apply_autofilter,
    bold_font,
    cell_value,
    new_workbook,
    workbook_to_bytes,
    write_header_row,
)

_RECEIPT_PAYMENT = "payment"


async def build_event_registrations_xlsx(
    db: AsyncSession,
    *,
    event_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    registration_status: list[str] | None = None,
    payment_status: list[str] | None = None,
    is_member_price: bool | None = None,
) -> bytes:
    stmt = (
        select(EventRegistration, Event, EventTariff, User, DoctorProfile, Payment)
        .join(Event, EventRegistration.event_id == Event.id)
        .join(EventTariff, EventRegistration.event_tariff_id == EventTariff.id)
        .join(User, EventRegistration.user_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .outerjoin(Payment, Payment.event_registration_id == EventRegistration.id)
    )

    conds: list[Any] = []
    if event_id is not None:
        conds.append(Event.id == event_id)
    elif date_from is not None and date_to is not None:
        lo, hi = msk_range_to_utc_exclusive_end(date_from, date_to)
        conds.append(Event.event_date >= lo)
        conds.append(Event.event_date < hi)

    if registration_status:
        conds.append(EventRegistration.status.in_(registration_status))

    if payment_status:
        conds.append(
            or_(
                Payment.id.is_(None),
                Payment.status.in_(payment_status),
            )
        )

    if is_member_price is not None:
        conds.append(EventRegistration.is_member_price.is_(is_member_price))

    cnt_q = (
        select(func.count(EventRegistration.id))
        .select_from(EventRegistration)
        .join(Event, EventRegistration.event_id == Event.id)
        .join(EventTariff, EventRegistration.event_tariff_id == EventTariff.id)
        .join(User, EventRegistration.user_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .outerjoin(Payment, Payment.event_registration_id == EventRegistration.id)
    )
    if conds:
        cnt_q = cnt_q.where(*conds)

    total = (await db.execute(cnt_q)).scalar() or 0
    if total > MAX_EXPORT_ROWS:
        raise ExportTooLargeError(total)

    if conds:
        stmt = stmt.where(*conds)
    stmt = stmt.order_by(Event.event_date.desc(), EventRegistration.created_at.desc())

    result = await db.execute(stmt)
    rows_orm = result.all()

    headers = [
        "ID мероприятия",
        "Название мероприятия",
        "Дата мероприятия",
        "Дата окончания",
        "Название тарифа",
        "Цена по тарифу (руб.)",
        "Тип участника",
        "ID регистрации",
        "Статус регистрации (EN)",
        "Статус регистрации (RU)",
        "Дата регистрации",
        "Имя гостя",
        "Email гостя",
        "Email для чека",
        "Email участника",
        "Фамилия",
        "Имя",
        "Отчество",
        "Телефон",
        "ID платежа",
        "Сумма платежа (руб.)",
        "Статус платежа (EN)",
        "Статус платежа (RU)",
        "Дата оплаты",
        "Ссылка на чек",
    ]

    wb, ws = new_workbook("Регистрации")
    write_header_row(ws, 1, headers)

    sum_succeeded = Decimal("0")
    reg_count = 0
    r = 2
    pid_to_row: dict[UUID, int] = {}
    for row in rows_orm:
        reg, ev, tariff, u, dp, pay = row
        reg_count += 1
        if pay and str(pay.status) == "succeeded":
            sum_succeeded += Decimal(str(pay.amount))
        if pay:
            pid_to_row[pay.id] = r

        member_label = (
            "Член ассоциации" if reg.is_member_price else "Внешний участник"
        )
        line = [
            str(ev.id),
            ev.title,
            format_date_msk(ev.event_date),
            format_date_msk(ev.event_end_date) if ev.event_end_date else None,
            tariff.name,
            float(reg.applied_price),
            member_label,
            str(reg.id),
            str(reg.status),
            ru_event_reg_status(str(reg.status)),
            format_dt_msk(reg.created_at),
            cell_value(reg.guest_full_name),
            cell_value(reg.guest_email),
            cell_value(reg.fiscal_email),
            u.email,
            cell_value(dp.last_name if dp else None),
            cell_value(dp.first_name if dp else None),
            cell_value(dp.middle_name if dp else None),
            cell_value(dp.phone if dp else None),
            str(pay.id) if pay else None,
            float(pay.amount) if pay else None,
            str(pay.status) if pay else None,
            ru_payment_status(str(pay.status)) if pay else None,
            format_dt_msk(pay.paid_at) if pay else None,
            None,
        ]
        for c_idx, val in enumerate(line, start=1):
            ws.cell(row=r, column=c_idx, value=val)
        r += 1

    if pid_to_row:
        pids = list(pid_to_row.keys())
        rq = (
            select(Receipt)
            .where(
                Receipt.payment_id.in_(pids),
                Receipt.receipt_type == _RECEIPT_PAYMENT,
            )
            .order_by(Receipt.payment_id, Receipt.created_at.desc())
        )
        rec_rows = (await db.execute(rq)).scalars().all()
        seen: set[UUID] = set()
        for rec in rec_rows:
            if rec.payment_id in seen:
                continue
            seen.add(rec.payment_id)
            row_idx = pid_to_row.get(rec.payment_id)
            if row_idx:
                ws.cell(row=row_idx, column=24, value=rec.receipt_url)

    last_data_row = r - 1
    if last_data_row >= 1:
        apply_autofilter(ws, len(headers), last_data_row)

    if last_data_row >= 1:
        r += 1
        ws.cell(row=r, column=1, value=f"Итого: регистраций {reg_count}").font = bold_font()
        ws.cell(row=r, column=21, value=float(sum_succeeded)).font = bold_font()

    return workbook_to_bytes(wb)
