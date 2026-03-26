"""XLSX export: doctor registry (management)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import String, and_, case, exists, func, not_, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cities import City
from app.models.profiles import DoctorProfile
from app.models.subscriptions import Plan, Subscription
from app.models.users import Role, User, UserRoleAssignment
from app.services.exports.active_member import is_active_member
from app.services.exports.export_errors import ExportTooLargeError
from app.services.exports.limits import MAX_EXPORT_ROWS
from app.services.exports.msk import format_date_msk, format_dt_msk, msk_now, msk_range_to_utc_exclusive_end
from app.services.exports.translations import (
    ru_board_role,
    ru_doctor_status,
    ru_subscription_status,
)
from app.services.exports.xlsx_base import (
    apply_autofilter,
    bold_font,
    cell_value,
    new_workbook,
    workbook_to_bytes,
    write_header_row,
)

_MSK = ZoneInfo("Europe/Moscow")

HEADERS = [
    "ID пользователя",
    "ID профиля врача",
    "Slug профиля",
    "Email (учётный)",
    "Фамилия",
    "Имя",
    "Отчество",
    "Телефон",
    "Email (публичный)",
    "Телефон (публичный)",
    "Город",
    "Статус профиля (EN)",
    "Статус профиля (RU)",
    "Активный член ассоциации",
    "Роль в правлении (EN)",
    "Роль в правлении (RU)",
    "Освобождён от вступ. взноса",
    "Дата исключения",
    "Дата регистрации аккаунта",
    "Дата создания профиля врача",
    "Профиль удалён",
    "Роли (перечень)",
    "Аккаунт активен",
    "Email подтверждён",
    "ID подписки",
    "Статус подписки (EN)",
    "Статус подписки (RU)",
    "Название плана",
    "Дата начала подписки",
    "Дата окончания подписки",
    "Дней до истечения",
    "Первый год / Продление",
]


def _bool_yn(v: bool | None) -> str:
    if v is None:
        return ""
    return "Да" if v else "Нет"


def _days_until_expiry(ends_at: datetime | None) -> int | None:
    if ends_at is None:
        return None
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=UTC)
    end_d = ends_at.astimezone(_MSK).date()
    today_d = msk_now().date()
    return (end_d - today_d).days


def _subscription_period_label(is_first_year: bool | None) -> str:
    if is_first_year is None:
        return ""
    return "Первый год" if is_first_year else "Продление"


def _best_subscription_subquery():
    """Одна строка подписки на пользователя: сначала активная, иначе последняя по датам."""
    rn = func.row_number().over(
        partition_by=Subscription.user_id,
        order_by=(
            case((Subscription.status == "active", 0), else_=1),
            func.coalesce(
                Subscription.ends_at,
                Subscription.starts_at,
                Subscription.created_at,
            ).desc().nulls_last(),
        ),
    ).label("sub_rn")
    inner = (
        select(
            Subscription.id.label("sub_id"),
            Subscription.user_id.label("sub_uid"),
            Subscription.status.label("sub_status"),
            Subscription.starts_at.label("sub_starts"),
            Subscription.ends_at.label("sub_ends"),
            Subscription.is_first_year.label("sub_first"),
            Plan.name.label("plan_name"),
            rn,
        )
        .select_from(
            Subscription.__table__.join(Plan.__table__, Subscription.plan_id == Plan.id)
        )
    ).subquery()
    return select(inner).where(inner.c.sub_rn == 1).subquery()


def _roles_subquery():
    return (
        select(
            UserRoleAssignment.user_id.label("r_uid"),
            func.string_agg(sql_cast(Role.name, String), ", ").label("roles_str"),
        )
        .select_from(
            UserRoleAssignment.__table__.join(Role.__table__, Role.id == UserRoleAssignment.role_id)
        )
        .group_by(UserRoleAssignment.user_id)
    ).subquery()


def _base_where(
    *,
    now_utc: datetime,
    status_list: list[str] | None,
    city_ids: list[UUID] | None,
    has_active_subscription: bool | None,
    board_roles: list[str] | None,
    entry_fee_exempt: bool | None,
    membership_excluded: bool | None,
    include_deleted_profiles: bool,
    created_from: date | None,
    created_to: date | None,
) -> list[Any]:
    conds: list[Any] = []
    if not include_deleted_profiles:
        conds.append(DoctorProfile.is_deleted.is_(False))
    if status_list:
        conds.append(DoctorProfile.status.in_(status_list))
    if city_ids:
        conds.append(DoctorProfile.city_id.in_(city_ids))
    if board_roles:
        conds.append(DoctorProfile.board_role.in_(board_roles))
    if entry_fee_exempt is not None:
        conds.append(DoctorProfile.entry_fee_exempt.is_(entry_fee_exempt))
    if membership_excluded is True:
        conds.append(DoctorProfile.membership_excluded_at.isnot(None))
    elif membership_excluded is False:
        conds.append(DoctorProfile.membership_excluded_at.is_(None))

    if created_from is not None and created_to is not None:
        lo, hi = msk_range_to_utc_exclusive_end(created_from, created_to)
        conds.append(User.created_at >= lo)
        conds.append(User.created_at < hi)

    active_sub = exists(
        select(Subscription.id).where(
            Subscription.user_id == User.id,
            Subscription.status == "active",
            or_(Subscription.ends_at.is_(None), Subscription.ends_at >= now_utc),
        )
    )
    if has_active_subscription is True:
        conds.append(active_sub)
    elif has_active_subscription is False:
        conds.append(not_(active_sub))

    return conds


def _active_member_rank(best_sub: Any, now_utc: datetime) -> Any:
    return case(
        (
            and_(
                DoctorProfile.is_deleted.is_(False),
                DoctorProfile.status == "active",
                DoctorProfile.membership_excluded_at.is_(None),
                best_sub.c.sub_id.isnot(None),
                best_sub.c.sub_status == "active",
                or_(best_sub.c.sub_ends.is_(None), best_sub.c.sub_ends >= now_utc),
            ),
            0,
        ),
        else_=1,
    )


async def build_doctors_xlsx(
    db: AsyncSession,
    *,
    status_list: list[str] | None = None,
    city_ids: list[UUID] | None = None,
    has_active_subscription: bool | None = None,
    board_roles: list[str] | None = None,
    entry_fee_exempt: bool | None = None,
    membership_excluded: bool | None = None,
    include_deleted_profiles: bool = False,
    created_from: date | None = None,
    created_to: date | None = None,
) -> bytes:
    now_utc = datetime.now(UTC)
    best_sub = _best_subscription_subquery()
    roles_sq = _roles_subquery()

    conds = _base_where(
        now_utc=now_utc,
        status_list=status_list,
        city_ids=city_ids,
        has_active_subscription=has_active_subscription,
        board_roles=board_roles,
        entry_fee_exempt=entry_fee_exempt,
        membership_excluded=membership_excluded,
        include_deleted_profiles=include_deleted_profiles,
        created_from=created_from,
        created_to=created_to,
    )

    base_from = (
        DoctorProfile.__table__.join(User.__table__, DoctorProfile.user_id == User.id)
        .outerjoin(City.__table__, DoctorProfile.city_id == City.id)
        .outerjoin(best_sub, best_sub.c.sub_uid == User.id)
        .outerjoin(roles_sq, roles_sq.c.r_uid == User.id)
    )

    cnt_q = select(func.count(DoctorProfile.id)).select_from(base_from)
    if conds:
        cnt_q = cnt_q.where(*conds)
    total = (await db.execute(cnt_q)).scalar() or 0
    if total > MAX_EXPORT_ROWS:
        raise ExportTooLargeError(total)

    am_rank = _active_member_rank(best_sub, now_utc)
    q = (
        select(
            DoctorProfile,
            User,
            City.name.label("city_name"),
            best_sub.c.sub_id,
            best_sub.c.sub_status,
            best_sub.c.sub_starts,
            best_sub.c.sub_ends,
            best_sub.c.sub_first,
            best_sub.c.plan_name,
            roles_sq.c.roles_str,
        )
        .select_from(base_from)
        .order_by(am_rank.asc(), DoctorProfile.last_name.asc(), DoctorProfile.first_name.asc())
    )
    if conds:
        q = q.where(*conds)

    rows = (await db.execute(q)).all()

    wb, ws = new_workbook("Врачи")
    write_header_row(ws, 1, HEADERS)
    col_n = len(HEADERS)

    active_yes = 0
    city_ids_seen: set[UUID | None] = set()

    for r_i, row in enumerate(rows, start=2):
        dp: DoctorProfile = row[0]
        user: User = row[1]
        city_name = row[2]
        sub_id = row[3]
        sub_status = row[4]
        sub_starts = row[5]
        sub_ends = row[6]
        sub_first = row[7]
        plan_name = row[8]
        roles_str = row[9]

        sub_like = (
            SimpleNamespace(status=sub_status, ends_at=sub_ends) if sub_id is not None else None
        )
        member_label = is_active_member(dp, sub_like, now=now_utc)
        if member_label == "Да":
            active_yes += 1
        city_ids_seen.add(dp.city_id)

        vals = [
            str(user.id),
            str(dp.id),
            dp.slug,
            user.email,
            dp.last_name,
            dp.first_name,
            dp.middle_name,
            dp.phone,
            dp.public_email,
            dp.public_phone,
            city_name,
            str(dp.status),
            ru_doctor_status(str(dp.status)),
            member_label,
            dp.board_role or "",
            ru_board_role(dp.board_role) if dp.board_role else "",
            _bool_yn(dp.entry_fee_exempt),
            format_dt_msk(dp.membership_excluded_at),
            format_dt_msk(user.created_at),
            format_dt_msk(dp.created_at),
            _bool_yn(dp.is_deleted),
            roles_str or "",
            _bool_yn(user.is_active),
            "Да" if user.email_verified_at else "Нет",
            str(sub_id) if sub_id else None,
            str(sub_status) if sub_status else None,
            ru_subscription_status(str(sub_status)) if sub_status else "",
            plan_name,
            format_date_msk(sub_starts) if sub_starts else None,
            format_date_msk(sub_ends) if sub_ends else None,
            _days_until_expiry(sub_ends),
            _subscription_period_label(sub_first),
        ]
        for c_i, v in enumerate(vals, start=1):
            ws.cell(row=r_i, column=c_i, value=cell_value(v))

    last_data_row = 1 + len(rows)
    if rows:
        tot_row = last_data_row + 1
        unique_cities = len({c for c in city_ids_seen if c is not None})
        ws.cell(row=tot_row, column=1, value="Итого")
        ws.cell(row=tot_row, column=1).font = bold_font()
        ws.cell(row=tot_row, column=2, value=f"Строк: {len(rows)}")
        ws.cell(row=tot_row, column=2).font = bold_font()
        ws.cell(row=tot_row, column=3, value=f"Активный член = Да: {active_yes}")
        ws.cell(row=tot_row, column=3).font = bold_font()
        ws.cell(row=tot_row, column=4, value=f"Уникальных городов: {unique_cities}")
        ws.cell(row=tot_row, column=4).font = bold_font()
        apply_autofilter(ws, col_n, tot_row)
    else:
        apply_autofilter(ws, col_n, 1)

    return workbook_to_bytes(wb)
