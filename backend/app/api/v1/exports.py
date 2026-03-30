"""XLSX exports: finance (accountant, manager, admin); doctors/protocol-history also for accountant."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
from app.core.security import require_role
from app.services.export_telegram_delivery import deliver_xlsx_to_telegram
from app.services.exports.export_errors import ExportTooLargeError
from app.services.exports.limits import LIMIT_EXCEEDED_MESSAGE
from app.services.exports.payloads import (
    arrears_payload,
    doctors_payload,
    event_registrations_payload,
    payments_payload,
    protocol_history_payload,
    subscriptions_payload,
)

router = APIRouter(prefix="/exports")

STAFF_FINANCE = require_role("admin", "manager", "accountant")
# Doctors + protocol history exports: admin, manager, accountant
STAFF_MANAGEMENT_EXPORTS = require_role("admin", "manager", "accountant")

XLSX_MEDIA = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _too_many(e: ExportTooLargeError) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=LIMIT_EXCEEDED_MESSAGE.format(n=e.count),
    )


def _tg_caption(title: str, filename: str) -> str:
    return f"{title}\n📎 {filename}"


@router.get(
    "/payments",
    summary="Выгрузка всех платежей (XLSX)",
    responses=error_responses(400, 401, 403),
)
async def export_payments(
    _: dict[str, Any] = STAFF_FINANCE,
    db: AsyncSession = Depends(get_db_session),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    date_field: str = Query(
        "paid_at",
        description="paid_at | created_at",
    ),
    status: Annotated[list[str] | None, Query()] = None,
    product_type: Annotated[list[str] | None, Query()] = None,
    payment_provider: Annotated[list[str] | None, Query()] = None,
    user_id: UUID | None = Query(None),
) -> Response:
    try:
        data, fname = await payments_payload(
            db,
            date_from=date_from,
            date_to=date_to,
            date_field=date_field,
            status=status,
            product_type=product_type,
            payment_provider=payment_provider,
            user_id=user_id,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e

    return Response(
        content=data,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post(
    "/payments/telegram",
    summary="Отправить выгрузку платежей в Telegram (XLSX)",
    responses=error_responses(400, 401, 403, 502, 503),
)
async def export_payments_telegram(
    _: dict[str, Any] = STAFF_FINANCE,
    db: AsyncSession = Depends(get_db_session),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    date_field: str = Query("paid_at"),
    status: Annotated[list[str] | None, Query()] = None,
    product_type: Annotated[list[str] | None, Query()] = None,
    payment_provider: Annotated[list[str] | None, Query()] = None,
    user_id: UUID | None = Query(None),
) -> dict[str, Any]:
    try:
        data, fname = await payments_payload(
            db,
            date_from=date_from,
            date_to=date_to,
            date_field=date_field,
            status=status,
            product_type=product_type,
            payment_provider=payment_provider,
            user_id=user_id,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e
    tg = await deliver_xlsx_to_telegram(
        data=data,
        filename=fname,
        caption=_tg_caption("Платежи", fname),
    )
    mid = (tg.get("result") or {}).get("message_id")
    return {"ok": True, "filename": fname, "telegram_message_id": mid}


@router.get(
    "/arrears",
    summary="Выгрузка задолженностей (XLSX)",
    responses=error_responses(400, 401, 403),
)
async def export_arrears(
    _: dict[str, Any] = STAFF_FINANCE,
    db: AsyncSession = Depends(get_db_session),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: Annotated[list[str] | None, Query()] = None,
    year: Annotated[list[int] | None, Query()] = None,
    user_id: UUID | None = Query(None),
) -> Response:
    try:
        data, fname = await arrears_payload(
            db,
            date_from=date_from,
            date_to=date_to,
            status=status,
            year=year,
            user_id=user_id,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e

    return Response(
        content=data,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post(
    "/arrears/telegram",
    summary="Отправить выгрузку задолженностей в Telegram (XLSX)",
    responses=error_responses(400, 401, 403, 502, 503),
)
async def export_arrears_telegram(
    _: dict[str, Any] = STAFF_FINANCE,
    db: AsyncSession = Depends(get_db_session),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: Annotated[list[str] | None, Query()] = None,
    year: Annotated[list[int] | None, Query()] = None,
    user_id: UUID | None = Query(None),
) -> dict[str, Any]:
    try:
        data, fname = await arrears_payload(
            db,
            date_from=date_from,
            date_to=date_to,
            status=status,
            year=year,
            user_id=user_id,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e
    tg = await deliver_xlsx_to_telegram(
        data=data, filename=fname, caption=_tg_caption("Задолженности", fname)
    )
    mid = (tg.get("result") or {}).get("message_id")
    return {"ok": True, "filename": fname, "telegram_message_id": mid}


@router.get(
    "/event-registrations",
    summary="Выгрузка регистраций на мероприятия (XLSX)",
    responses=error_responses(400, 401, 403),
)
async def export_event_registrations(
    _: dict[str, Any] = STAFF_FINANCE,
    db: AsyncSession = Depends(get_db_session),
    event_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    registration_status: Annotated[list[str] | None, Query()] = None,
    payment_status: Annotated[list[str] | None, Query()] = None,
    is_member_price: bool | None = Query(None),
) -> Response:
    try:
        data, fname = await event_registrations_payload(
            db,
            event_id=event_id,
            date_from=date_from,
            date_to=date_to,
            registration_status=registration_status,
            payment_status=payment_status,
            is_member_price=is_member_price,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e

    return Response(
        content=data,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post(
    "/event-registrations/telegram",
    summary="Отправить выгрузку регистраций в Telegram (XLSX)",
    responses=error_responses(400, 401, 403, 502, 503),
)
async def export_event_registrations_telegram(
    _: dict[str, Any] = STAFF_FINANCE,
    db: AsyncSession = Depends(get_db_session),
    event_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    registration_status: Annotated[list[str] | None, Query()] = None,
    payment_status: Annotated[list[str] | None, Query()] = None,
    is_member_price: bool | None = Query(None),
) -> dict[str, Any]:
    try:
        data, fname = await event_registrations_payload(
            db,
            event_id=event_id,
            date_from=date_from,
            date_to=date_to,
            registration_status=registration_status,
            payment_status=payment_status,
            is_member_price=is_member_price,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e
    tg = await deliver_xlsx_to_telegram(
        data=data,
        filename=fname,
        caption=_tg_caption("Регистрации на мероприятия", fname),
    )
    mid = (tg.get("result") or {}).get("message_id")
    return {"ok": True, "filename": fname, "telegram_message_id": mid}


@router.get(
    "/subscriptions",
    summary="Выгрузка подписок и взносов (XLSX)",
    responses=error_responses(400, 401, 403),
)
async def export_subscriptions(
    _: dict[str, Any] = STAFF_FINANCE,
    db: AsyncSession = Depends(get_db_session),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: Annotated[list[str] | None, Query()] = None,
    plan_id: Annotated[list[UUID] | None, Query()] = None,
    plan_type: Annotated[list[str] | None, Query()] = None,
    is_first_year: bool | None = Query(None),
    active_on: date | None = Query(None, description="Подписки, активные на дату"),
    user_id: UUID | None = Query(None),
) -> Response:
    try:
        data, fname = await subscriptions_payload(
            db,
            date_from=date_from,
            date_to=date_to,
            status=status,
            plan_id=plan_id,
            plan_type=plan_type,
            is_first_year=is_first_year,
            active_on=active_on,
            user_id=user_id,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e

    return Response(
        content=data,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post(
    "/subscriptions/telegram",
    summary="Отправить выгрузку подписок в Telegram (XLSX)",
    responses=error_responses(400, 401, 403, 502, 503),
)
async def export_subscriptions_telegram(
    _: dict[str, Any] = STAFF_FINANCE,
    db: AsyncSession = Depends(get_db_session),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: Annotated[list[str] | None, Query()] = None,
    plan_id: Annotated[list[UUID] | None, Query()] = None,
    plan_type: Annotated[list[str] | None, Query()] = None,
    is_first_year: bool | None = Query(None),
    active_on: date | None = Query(None),
    user_id: UUID | None = Query(None),
) -> dict[str, Any]:
    try:
        data, fname = await subscriptions_payload(
            db,
            date_from=date_from,
            date_to=date_to,
            status=status,
            plan_id=plan_id,
            plan_type=plan_type,
            is_first_year=is_first_year,
            active_on=active_on,
            user_id=user_id,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e
    tg = await deliver_xlsx_to_telegram(
        data=data, filename=fname, caption=_tg_caption("Подписки", fname)
    )
    mid = (tg.get("result") or {}).get("message_id")
    return {"ok": True, "filename": fname, "telegram_message_id": mid}


@router.get(
    "/doctors",
    summary="Управленческая выгрузка: реестр врачей (XLSX)",
    responses=error_responses(400, 401, 403),
)
async def export_doctors(
    _: dict[str, Any] = STAFF_MANAGEMENT_EXPORTS,
    db: AsyncSession = Depends(get_db_session),
    status: Annotated[list[str] | None, Query()] = None,
    city_id: Annotated[list[UUID] | None, Query()] = None,
    has_active_subscription: bool | None = Query(None),
    board_role: Annotated[list[str] | None, Query()] = None,
    entry_fee_exempt: bool | None = Query(None),
    membership_excluded: bool | None = Query(None),
    is_deleted: bool = Query(False, description="true — включить удалённые профили"),
    created_from: date | None = Query(None),
    created_to: date | None = Query(None),
) -> Response:
    try:
        data, fname = await doctors_payload(
            db,
            status=status,
            city_id=city_id,
            has_active_subscription=has_active_subscription,
            board_role=board_role,
            entry_fee_exempt=entry_fee_exempt,
            membership_excluded=membership_excluded,
            is_deleted=is_deleted,
            created_from=created_from,
            created_to=created_to,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e

    return Response(
        content=data,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post(
    "/doctors/telegram",
    summary="Отправить реестр врачей в Telegram (XLSX)",
    responses=error_responses(400, 401, 403, 502, 503),
)
async def export_doctors_telegram(
    _: dict[str, Any] = STAFF_MANAGEMENT_EXPORTS,
    db: AsyncSession = Depends(get_db_session),
    status: Annotated[list[str] | None, Query()] = None,
    city_id: Annotated[list[UUID] | None, Query()] = None,
    has_active_subscription: bool | None = Query(None),
    board_role: Annotated[list[str] | None, Query()] = None,
    entry_fee_exempt: bool | None = Query(None),
    membership_excluded: bool | None = Query(None),
    is_deleted: bool = Query(False),
    created_from: date | None = Query(None),
    created_to: date | None = Query(None),
) -> dict[str, Any]:
    try:
        data, fname = await doctors_payload(
            db,
            status=status,
            city_id=city_id,
            has_active_subscription=has_active_subscription,
            board_role=board_role,
            entry_fee_exempt=entry_fee_exempt,
            membership_excluded=membership_excluded,
            is_deleted=is_deleted,
            created_from=created_from,
            created_to=created_to,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e
    tg = await deliver_xlsx_to_telegram(
        data=data, filename=fname, caption=_tg_caption("Реестр врачей", fname)
    )
    mid = (tg.get("result") or {}).get("message_id")
    return {"ok": True, "filename": fname, "telegram_message_id": mid}


@router.get(
    "/protocol-history",
    summary="Управленческая выгрузка: история протоколов (XLSX)",
    responses=error_responses(400, 401, 403),
)
async def export_protocol_history(
    _: dict[str, Any] = STAFF_MANAGEMENT_EXPORTS,
    db: AsyncSession = Depends(get_db_session),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    year: Annotated[list[int] | None, Query()] = None,
    action_type: Annotated[list[str] | None, Query()] = None,
    doctor_user_id: UUID | None = Query(None),
    created_by_user_id: UUID | None = Query(None),
    active_doctors_only: bool = Query(False),
) -> Response:
    try:
        data, fname = await protocol_history_payload(
            db,
            date_from=date_from,
            date_to=date_to,
            year=year,
            action_type=action_type,
            doctor_user_id=doctor_user_id,
            created_by_user_id=created_by_user_id,
            active_doctors_only=active_doctors_only,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e

    return Response(
        content=data,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post(
    "/protocol-history/telegram",
    summary="Отправить историю протоколов в Telegram (XLSX)",
    responses=error_responses(400, 401, 403, 502, 503),
)
async def export_protocol_history_telegram(
    _: dict[str, Any] = STAFF_MANAGEMENT_EXPORTS,
    db: AsyncSession = Depends(get_db_session),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    year: Annotated[list[int] | None, Query()] = None,
    action_type: Annotated[list[str] | None, Query()] = None,
    doctor_user_id: UUID | None = Query(None),
    created_by_user_id: UUID | None = Query(None),
    active_doctors_only: bool = Query(False),
) -> dict[str, Any]:
    try:
        data, fname = await protocol_history_payload(
            db,
            date_from=date_from,
            date_to=date_to,
            year=year,
            action_type=action_type,
            doctor_user_id=doctor_user_id,
            created_by_user_id=created_by_user_id,
            active_doctors_only=active_doctors_only,
        )
    except ExportTooLargeError as e:
        raise _too_many(e) from e
    tg = await deliver_xlsx_to_telegram(
        data=data, filename=fname, caption=_tg_caption("История протоколов", fname)
    )
    mid = (tg.get("result") or {}).get("message_id")
    return {"ok": True, "filename": fname, "telegram_message_id": mid}
