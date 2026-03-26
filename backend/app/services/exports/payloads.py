"""Shared export builders: (xlsx bytes, filename) for GET responses and Telegram delivery."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.exports.arrears_export import build_arrears_xlsx
from app.services.exports.doctors_export import build_doctors_xlsx
from app.services.exports.event_registrations_export import build_event_registrations_xlsx
from app.services.exports.export_errors import ExportTooLargeError
from app.services.exports.msk import default_month_date_range, default_year_date_range_msk, msk_now
from app.services.exports.payments_export import build_payments_xlsx
from app.services.exports.protocol_history_export import build_protocol_history_xlsx
from app.services.exports.subscriptions_export import build_subscriptions_xlsx


async def payments_payload(
    db: AsyncSession,
    *,
    date_from: date | None,
    date_to: date | None,
    date_field: str,
    status: list[str] | None,
    product_type: list[str] | None,
    payment_provider: list[str] | None,
    user_id: UUID | None,
) -> tuple[bytes, str]:
    if date_from is None and date_to is None:
        date_from, date_to = default_month_date_range()
    elif date_from is None or date_to is None:
        raise HTTPException(
            status_code=422,
            detail="Укажите оба параметра date_from и date_to или ни одного",
        )
    if date_field not in ("paid_at", "created_at"):
        raise HTTPException(status_code=422, detail="date_field: paid_at или created_at")

    data = await build_payments_xlsx(
        db,
        date_from=date_from,
        date_to=date_to,
        date_field=date_field,
        status_list=status,
        product_types=product_type,
        providers=payment_provider,
        user_id=user_id,
    )
    fname = f"payments_{date_from.isoformat()}_{date_to.isoformat()}.xlsx"
    return data, fname


async def arrears_payload(
    db: AsyncSession,
    *,
    date_from: date | None,
    date_to: date | None,
    status: list[str] | None,
    year: list[int] | None,
    user_id: UUID | None,
) -> tuple[bytes, str]:
    data = await build_arrears_xlsx(
        db,
        date_from=date_from,
        date_to=date_to,
        status_list=status,
        years=year,
        user_id=user_id,
    )
    tag_from = date_from.isoformat() if date_from else "all"
    tag_to = date_to.isoformat() if date_to else "all"
    return data, f"arrears_{tag_from}_{tag_to}.xlsx"


async def event_registrations_payload(
    db: AsyncSession,
    *,
    event_id: UUID | None,
    date_from: date | None,
    date_to: date | None,
    registration_status: list[str] | None,
    payment_status: list[str] | None,
    is_member_price: bool | None,
) -> tuple[bytes, str]:
    if event_id is None and (date_from is None or date_to is None):
        raise HTTPException(
            status_code=422,
            detail="Укажите event_id или пару date_from и date_to",
        )
    data = await build_event_registrations_xlsx(
        db,
        event_id=event_id,
        date_from=date_from,
        date_to=date_to,
        registration_status=registration_status,
        payment_status=payment_status,
        is_member_price=is_member_price,
    )
    if event_id:
        fname = f"event_registrations_{event_id}.xlsx"
    else:
        fname = f"event_registrations_{date_from}_{date_to}.xlsx"
    return data, fname


async def subscriptions_payload(
    db: AsyncSession,
    *,
    date_from: date | None,
    date_to: date | None,
    status: list[str] | None,
    plan_id: list[UUID] | None,
    plan_type: list[str] | None,
    is_first_year: bool | None,
    active_on: date | None,
    user_id: UUID | None,
) -> tuple[bytes, str]:
    data = await build_subscriptions_xlsx(
        db,
        date_from=date_from,
        date_to=date_to,
        status_list=status,
        plan_ids=plan_id,
        plan_types=plan_type,
        is_first_year=is_first_year,
        active_on=active_on,
        user_id=user_id,
    )
    tag_from = date_from.isoformat() if date_from else "all"
    tag_to = date_to.isoformat() if date_to else "all"
    return data, f"subscriptions_{tag_from}_{tag_to}.xlsx"


async def doctors_payload(
    db: AsyncSession,
    *,
    status: list[str] | None,
    city_id: list[UUID] | None,
    has_active_subscription: bool | None,
    board_role: list[str] | None,
    entry_fee_exempt: bool | None,
    membership_excluded: bool | None,
    is_deleted: bool,
    created_from: date | None,
    created_to: date | None,
) -> tuple[bytes, str]:
    if (created_from is None) ^ (created_to is None):
        raise HTTPException(
            status_code=422,
            detail="Укажите оба параметра created_from и created_to или ни одного",
        )
    data = await build_doctors_xlsx(
        db,
        status_list=status,
        city_ids=city_id,
        has_active_subscription=has_active_subscription,
        board_roles=board_role,
        entry_fee_exempt=entry_fee_exempt,
        membership_excluded=membership_excluded,
        include_deleted_profiles=is_deleted,
        created_from=created_from,
        created_to=created_to,
    )
    return data, f"doctors_{msk_now().date().isoformat()}.xlsx"


async def protocol_history_payload(
    db: AsyncSession,
    *,
    date_from: date | None,
    date_to: date | None,
    year: list[int] | None,
    action_type: list[str] | None,
    doctor_user_id: UUID | None,
    created_by_user_id: UUID | None,
    active_doctors_only: bool,
) -> tuple[bytes, str]:
    if (date_from is None) ^ (date_to is None):
        raise HTTPException(
            status_code=422,
            detail="Укажите оба параметра date_from и date_to или ни одного",
        )

    apply_date_filter: bool
    df: date | None
    dt: date | None

    if doctor_user_id is not None:
        if date_from is None and date_to is None:
            apply_date_filter = False
            df, dt = None, None
        else:
            apply_date_filter = True
            df, dt = date_from, date_to
    elif date_from is None and date_to is None:
        df, dt = default_year_date_range_msk()
        apply_date_filter = True
    else:
        apply_date_filter = True
        df, dt = date_from, date_to

    data = await build_protocol_history_xlsx(
        db,
        date_from=df,
        date_to=dt,
        apply_date_filter=apply_date_filter,
        years=year,
        action_types=action_type,
        doctor_user_id=doctor_user_id,
        created_by_user_id=created_by_user_id,
        active_doctors_only=active_doctors_only,
    )
    if doctor_user_id is not None and not apply_date_filter:
        fname = f"protocol_history_doctor_{doctor_user_id}.xlsx"
    else:
        fname = f"protocol_history_{df.isoformat()}_{dt.isoformat()}.xlsx"
    return data, fname


__all__ = [
    "arrears_payload",
    "doctors_payload",
    "event_registrations_payload",
    "payments_payload",
    "protocol_history_payload",
    "subscriptions_payload",
]
