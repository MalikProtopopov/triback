"""XLSX export: all payments."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, desc, func, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arrears import MembershipArrear
from app.models.events import Event, EventRegistration, EventTariff
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Plan, Receipt, Subscription
from app.models.users import User
from app.services.exports.export_errors import ExportTooLargeError
from app.services.exports.limits import MAX_EXPORT_ROWS
from app.services.exports.msk import format_date_msk, format_dt_msk, msk_range_to_utc_exclusive_end
from app.services.exports.translations import (
    PRODUCT_TYPE_RU,
    ru_payment_status,
    ru_product_type,
    ru_receipt_status,
)
from app.services.exports.xlsx_base import (
    apply_autofilter,
    bold_font,
    cell_value,
    new_workbook,
    workbook_to_bytes,
    write_header_row,
)

_RECEIPT_TYPE_PAYMENT = "payment"


def _product_description(
    product_type: str,
    *,
    plan_name: str | None,
    plan_code: str | None,
    starts_at: datetime | None,
    ends_at: datetime | None,
    event_title: str | None,
    event_date: datetime | None,
    tariff_name: str | None,
    is_member_price: bool | None,
    arrear_year: int | None,
    arrear_amount: Decimal | float | None,
    raw_description: str | None,
) -> str:
    if product_type in ("subscription", "entry_fee"):
        label = PRODUCT_TYPE_RU.get(product_type, product_type)
        if plan_name and plan_code:
            base = f"{label} / {plan_name} ({plan_code})"
        elif plan_name:
            base = f"{label} / {plan_name}"
        else:
            base = label
        if starts_at and ends_at:
            p_from = format_date_msk(starts_at) or ""
            p_to = format_date_msk(ends_at) or ""
            period = f"{p_from}–{p_to}"
            return f"{base} / {period}"
        if starts_at and ends_at is None:
            return f"{base} / бессрочно"
        return base
    if product_type == "event":
        if not event_title:
            return raw_description or "—"
        ed = format_date_msk(event_date) if event_date else "—"
        tn = tariff_name or "—"
        member = (
            "цена члена" if is_member_price else "цена не члена"
        )
        return f"{event_title} / {ed} / тариф: {tn} / {member}"
    if product_type == "membership_arrears":
        if arrear_year is not None and arrear_amount is not None:
            amt = float(arrear_amount)
            return f"Задолженность {arrear_year} г. / {amt:.2f} руб."
        return raw_description or "—"
    return raw_description or "—"


def _payment_export_filters(
    *,
    date_from: date,
    date_to: date,
    date_field: str,
    status_list: list[str] | None,
    product_types: list[str] | None,
    providers: list[str] | None,
    user_id: UUID | None,
) -> list[Any]:
    lo, hi = msk_range_to_utc_exclusive_end(date_from, date_to)
    col = Payment.paid_at if date_field == "paid_at" else Payment.created_at
    conds: list[Any] = [col >= lo, col < hi]
    if status_list:
        conds.append(Payment.status.in_(status_list))
    if product_types:
        conds.append(Payment.product_type.in_(product_types))
    if providers:
        conds.append(Payment.payment_provider.in_(providers))
    if user_id:
        conds.append(Payment.user_id == user_id)
    return conds


def _payments_select() -> Select[Any]:
    return (
        select(
            Payment,
            User,
            DoctorProfile,
            Subscription,
            Plan,
            EventRegistration,
            Event,
            EventTariff,
            MembershipArrear,
        )
        .join(User, Payment.user_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .outerjoin(Subscription, Subscription.id == Payment.subscription_id)
        .outerjoin(Plan, Plan.id == Subscription.plan_id)
        .outerjoin(EventRegistration, EventRegistration.id == Payment.event_registration_id)
        .outerjoin(Event, Event.id == EventRegistration.event_id)
        .outerjoin(EventTariff, EventTariff.id == EventRegistration.event_tariff_id)
        .outerjoin(MembershipArrear, MembershipArrear.id == Payment.arrear_id)
    )


async def _latest_receipts_map(
    db: AsyncSession, payment_ids: list[UUID]
) -> dict[UUID, Receipt]:
    if not payment_ids:
        return {}
    q = (
        select(Receipt)
        .where(
            Receipt.payment_id.in_(payment_ids),
            Receipt.receipt_type == _RECEIPT_TYPE_PAYMENT,
        )
        .order_by(Receipt.payment_id, Receipt.created_at.desc())
    )
    rows = (await db.execute(q)).scalars().all()
    out: dict[UUID, Receipt] = {}
    for r in rows:
        if r.payment_id not in out:
            out[r.payment_id] = r
    return out


async def build_payments_xlsx(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    date_field: str = "paid_at",
    status_list: list[str] | None = None,
    product_types: list[str] | None = None,
    providers: list[str] | None = None,
    user_id: UUID | None = None,
) -> bytes:
    conds = _payment_export_filters(
        date_from=date_from,
        date_to=date_to,
        date_field=date_field,
        status_list=status_list,
        product_types=product_types,
        providers=providers,
        user_id=user_id,
    )

    cnt_q = select(func.count(Payment.id)).select_from(Payment).where(*conds)
    total = (await db.execute(cnt_q)).scalar() or 0
    if total > MAX_EXPORT_ROWS:
        raise ExportTooLargeError(total)

    stmt = _payments_select().where(*conds).order_by(nulls_last(desc(Payment.paid_at)))
    result = await db.execute(stmt)
    rows_orm = result.all()

    pids = [row[0].id for row in rows_orm]
    receipt_map = await _latest_receipts_map(db, pids)

    headers = [
        "ID платежа (системный)",
        "ID платежа (провайдер)",
        "ID операции Moneta",
        "Email плательщика",
        "Фамилия",
        "Имя",
        "Отчество",
        "Телефон",
        "Сумма (руб.)",
        "Статус (EN)",
        "Статус (RU)",
        "Провайдер",
        "Дата создания",
        "Дата оплаты",
        "Описание (сырое)",
        "Тип продукта (EN)",
        "Тип продукта (RU)",
        "Что оплачено",
        "Ссылка на чек",
        "Статус чека (фиск.)",
        "Email для чека",
    ]

    wb, ws = new_workbook("Платежи")
    write_header_row(ws, 1, headers)

    succeeded_total = Decimal("0")
    r = 2
    for row in rows_orm:
        (
            p,
            u,
            dp,
            sub,
            plan,
            er,
            ev,
            tariff,
            arr,
        ) = row
        pt = str(p.product_type)
        what = _product_description(
            pt,
            plan_name=plan.name if plan else None,
            plan_code=plan.code if plan else None,
            starts_at=sub.starts_at if sub else None,
            ends_at=sub.ends_at if sub else None,
            event_title=ev.title if ev else None,
            event_date=ev.event_date if ev else None,
            tariff_name=tariff.name if tariff else None,
            is_member_price=er.is_member_price if er else None,
            arrear_year=arr.year if arr else None,
            arrear_amount=arr.amount if arr else None,
            raw_description=p.description,
        )
        rec = receipt_map.get(p.id)
        fiscal_email = er.fiscal_email if er and pt == "event" else None

        if str(p.status) == "succeeded":
            succeeded_total += Decimal(str(p.amount))

        cells = [
            str(p.id),
            cell_value(p.external_payment_id),
            cell_value(
                p.moneta_operation_id if str(p.payment_provider) == "moneta" else None
            ),
            u.email,
            cell_value(dp.last_name if dp else None),
            cell_value(dp.first_name if dp else None),
            cell_value(dp.middle_name if dp else None),
            cell_value(dp.phone if dp else None),
            float(p.amount),
            str(p.status),
            ru_payment_status(str(p.status)),
            str(p.payment_provider),
            format_dt_msk(p.created_at),
            format_dt_msk(p.paid_at),
            cell_value(p.description),
            pt,
            ru_product_type(pt),
            what,
            cell_value(rec.receipt_url if rec else None),
            ru_receipt_status(str(rec.status)) if rec else None,
            cell_value(fiscal_email),
        ]
        for c_idx, val in enumerate(cells, start=1):
            ws.cell(row=r, column=c_idx, value=val)
        r += 1

    last_data_row = r - 1
    if last_data_row >= 1:
        apply_autofilter(ws, len(headers), max(1, last_data_row))

    if last_data_row >= 1 and succeeded_total > 0:
        r += 1
        lbl = ws.cell(row=r, column=1, value="Итого (оплаченные)")
        lbl.font = bold_font()
        v = ws.cell(row=r, column=9, value=float(succeeded_total))
        v.font = bold_font()

    return workbook_to_bytes(wb)
