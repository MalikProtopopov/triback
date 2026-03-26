#!/usr/bin/env python3
"""Очистка БД: удаление врачей и портальных пользователей, нормализация ролей staff.

Файлы .env / переменные окружения скрипт НЕ читает и НЕ меняет — только подключение к БД
через уже настроенный DATABASE_URL у процесса.

НИКОГДА не удаляются (ни при каких флагах):
  • telegram_integrations — токен бота, webhook, owner_chat_id и пр. (единственная строка конфига).
  • certificate_settings — шаблоны сертификатов (подписи, логотипы, префикс номера и т.д.).
    Таблица выданных сертификатов certificates удаляется вместе с профилями врачей — это не
    то же самое, что certificate_settings.

При --wipe-auxiliary-data дополнительно очищаются служебные данные, но:
  • в site_settings сохраняются строки, у которых key начинается с «telegram» (например
    telegram_bot_link), чтобы не сбросить публичные/связанные с Telegram ключи.

Что делает (при --execute):
1. Нормализует роли сотрудников: у каждого с ролями admin/manager/accountant остаётся одна
   роль (приоритет: admin > manager > accountant).
2. Опционально (--wipe-auxiliary-data): протоколы, webhook-inbox, задолженности, уведомления,
   прочие site_settings (кроме ключей telegram*).
3. Удаляет врачей:
   - только врач (без staff): полное удаление пользователя;
   - врач + staff: снимается роль doctor, удаляется doctor_profile и связанное, staff сохраняется.
4. Опционально (--delete-portal-users): удаляет пользователей только с ролью user (без staff).

Пароли не меняются — хэши в БД сохраняются. Печатается список email staff.

ВАЖНО: сделайте бэкап БД перед --execute.

Usage (из каталога backend):
  poetry run python scripts/db_cleanup_doctors.py
  poetry run python scripts/db_cleanup_doctors.py --execute
  poetry run python scripts/db_cleanup_doctors.py --execute --wipe-auxiliary-data
  poetry run python scripts/db_cleanup_doctors.py --execute --delete-portal-users --report /tmp/report.txt
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

if __name__ == "__main__" and "__file__" in dir():
    _here = os.path.dirname(os.path.abspath(__file__))
    _backend = os.path.dirname(_here)
    if _backend not in sys.path:
        sys.path.insert(0, _backend)

from sqlalchemy import delete, func, not_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.arrears import MembershipArrear
from app.models.certificates import Certificate
from app.models.content import Article, ContentBlock
from app.models.events import Event
from app.models.payment_webhook_inbox import PaymentWebhookInbox
from app.models.profiles import DoctorProfile, ModerationHistory
from app.models.protocol_history import ProtocolHistoryEntry
from app.models.site import SiteSetting
from app.models.subscriptions import Payment, Receipt, Subscription
from app.models.users import Notification, Role, User, UserRoleAssignment
from app.models.voting import Vote, VotingCandidate, VotingSession

# TelegramIntegration и CertificateSettings намеренно не импортируются: эти таблицы не очищаются.

STAFF_ROLE_NAMES = ("admin", "manager", "accountant")
STAFF_PRIORITY = {"admin": 0, "manager": 1, "accountant": 2}

ROLES_SEED = [
    ("admin", "Администратор"),
    ("manager", "Менеджер"),
    ("accountant", "Бухгалтер"),
    ("doctor", "Врач"),
    ("user", "Пользователь"),
]


def _pick_staff_role(role_names: list[str]) -> str:
    ranked = [r for r in STAFF_ROLE_NAMES if r in role_names]
    if not ranked:
        raise RuntimeError("no staff role in list")
    return min(ranked, key=lambda r: STAFF_PRIORITY[r])


async def _role_map(session: AsyncSession) -> dict[str, Role]:
    for name, title in ROLES_SEED:
        r = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
        if r is None:
            session.add(Role(name=name, title=title))
            await session.flush()
    rows = (await session.execute(select(Role))).scalars().all()
    return {r.name: r for r in rows}


async def _fallback_admin_id(session: AsyncSession, role_map: dict[str, Role]) -> UUID:
    admin_rid = role_map["admin"].id
    uid = (
        await session.execute(
            select(UserRoleAssignment.user_id).where(UserRoleAssignment.role_id == admin_rid).limit(1)
        )
    ).scalar_one_or_none()
    if uid is None:
        raise SystemExit(
            "Нет пользователя с ролью admin. Создайте: python scripts/create_admin.py"
        )
    return uid


async def normalize_staff_roles(
    session: AsyncSession, role_map: dict[str, Role], dry_run: bool
) -> None:
    staff_ids = {role_map[n].id for n in STAFF_ROLE_NAMES}
    rows = (
        await session.execute(
            select(UserRoleAssignment, User, Role)
            .join(User, User.id == UserRoleAssignment.user_id)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(UserRoleAssignment.role_id.in_(staff_ids))
        )
    ).all()

    by_user: dict[UUID, list[tuple[UserRoleAssignment, User, Role]]] = defaultdict(list)
    for ura, user, role in rows:
        by_user[user.id].append((ura, user, role))

    for _uid, pairs in by_user.items():
        rnames = [p[2].name for p in pairs]
        staff_only = [n for n in rnames if n in STAFF_PRIORITY]
        if len(staff_only) <= 1:
            continue
        keep = _pick_staff_role(staff_only)
        u = pairs[0][1]
        before = ",".join(sorted(staff_only))
        print(f"Staff {u.email}: роли {before} -> оставить {keep}")
        for ura, role in pairs:
            if role.name != keep and role.name in STAFF_PRIORITY:
                if dry_run:
                    print(f"  [dry-run] delete UserRoleAssignment role={role.name}")
                else:
                    await session.delete(ura)


async def _clear_profile_voting(session: AsyncSession, profile_ids: list[UUID]) -> None:
    if not profile_ids:
        return
    cand_ids = (
        await session.execute(
            select(VotingCandidate.id).where(VotingCandidate.doctor_profile_id.in_(profile_ids))
        )
    ).scalars().all()
    if cand_ids:
        await session.execute(delete(Vote).where(Vote.candidate_id.in_(cand_ids)))
        await session.execute(delete(VotingCandidate).where(VotingCandidate.id.in_(cand_ids)))
    await session.execute(
        delete(ContentBlock).where(
            ContentBlock.entity_type == "doctor_profile",
            ContentBlock.entity_id.in_(profile_ids),
        )
    )


async def _purge_user_refs(session: AsyncSession, user_ids: list[UUID], fallback: UUID) -> None:
    if not user_ids:
        return
    pay_ids = (
        await session.execute(select(Payment.id).where(Payment.user_id.in_(user_ids)))
    ).scalars().all()
    if pay_ids:
        await session.execute(delete(Receipt).where(Receipt.payment_id.in_(pay_ids)))
        await session.execute(delete(Payment).where(Payment.id.in_(pay_ids)))
    await session.execute(delete(Subscription).where(Subscription.user_id.in_(user_ids)))
    await session.execute(delete(Vote).where(Vote.user_id.in_(user_ids)))
    await session.execute(
        update(Event).where(Event.created_by.in_(user_ids)).values(created_by=fallback)
    )
    await session.execute(
        update(Article).where(Article.author_id.in_(user_ids)).values(author_id=fallback)
    )
    await session.execute(
        update(VotingSession)
        .where(VotingSession.created_by.in_(user_ids))
        .values(created_by=fallback)
    )
    await session.execute(
        update(ModerationHistory)
        .where(ModerationHistory.admin_id.in_(user_ids))
        .values(admin_id=fallback)
    )
    await session.execute(
        update(ProtocolHistoryEntry)
        .where(ProtocolHistoryEntry.created_by_user_id.in_(user_ids))
        .values(created_by_user_id=fallback)
    )
    await session.execute(
        update(ProtocolHistoryEntry)
        .where(ProtocolHistoryEntry.last_edited_by_user_id.in_(user_ids))
        .values(last_edited_by_user_id=None)
    )


async def strip_doctor_from_staff(
    session: AsyncSession, user_id: UUID, role_map: dict[str, Role], dry_run: bool
) -> None:
    drid = role_map["doctor"].id
    ura = (
        await session.execute(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id == drid,
            )
        )
    ).scalar_one_or_none()
    if ura:
        if dry_run:
            print(f"  [dry-run] remove doctor role from staff user {user_id}")
        else:
            await session.delete(ura)

    prof = (
        await session.execute(select(DoctorProfile).where(DoctorProfile.user_id == user_id))
    ).scalar_one_or_none()
    if prof:
        pid = prof.id
        if dry_run:
            print(f"  [dry-run] delete doctor_profile {pid}")
        else:
            await _clear_profile_voting(session, [pid])
            await session.execute(delete(Certificate).where(Certificate.doctor_profile_id == pid))
            await session.delete(prof)


async def delete_users_full(
    session: AsyncSession,
    user_ids: list[UUID],
    fallback: UUID,
    dry_run: bool,
) -> None:
    user_ids = [u for u in user_ids if u != fallback]
    if not user_ids:
        return
    for uid in user_ids:
        u = await session.get(User, uid)
        print(f"Удалить пользователя полностью: {u.email if u else uid}")
    if dry_run:
        return
    await _purge_user_refs(session, user_ids, fallback)
    for uid in user_ids:
        prof = (
            await session.execute(select(DoctorProfile.id).where(DoctorProfile.user_id == uid))
        ).scalar_one_or_none()
        if prof:
            await _clear_profile_voting(session, [prof])
    await session.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id.in_(user_ids)))
    await session.execute(delete(User).where(User.id.in_(user_ids)))


async def _user_has_staff(session: AsyncSession, user_id: UUID, role_map: dict[str, Role]) -> bool:
    staff_ids = {role_map[n].id for n in STAFF_ROLE_NAMES}
    n = (
        await session.execute(
            select(func.count())
            .select_from(UserRoleAssignment)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id.in_(staff_ids),
            )
        )
    ).scalar_one()
    return int(n) > 0


async def wipe_auxiliary_business_data(session: AsyncSession, dry_run: bool) -> None:
    """Очистка служебных данных без трогания telegram_integrations и certificate_settings.

    site_settings: удаляются все строки, кроме тех, чей key начинается с «telegram»
    (например telegram_bot_link), чтобы сохранить публичную ссылку на бота и аналогичные ключи.
    """
    print("\n=== Вспомогательные данные (wipe-auxiliary-data) ===\n")

    n_ph = (
        await session.execute(select(func.count()).select_from(ProtocolHistoryEntry))
    ).scalar_one()
    n_inbox = (
        await session.execute(select(func.count()).select_from(PaymentWebhookInbox))
    ).scalar_one()
    n_arr = (
        await session.execute(select(func.count()).select_from(MembershipArrear))
    ).scalar_one()
    n_notif = (await session.execute(select(func.count()).select_from(Notification))).scalar_one()
    n_site = (await session.execute(select(func.count()).select_from(SiteSetting))).scalar_one()
    n_site_tg = (
        await session.execute(
            select(func.count()).select_from(SiteSetting).where(SiteSetting.key.like("telegram%"))
        )
    ).scalar_one()

    if dry_run:
        print(f"  [dry-run] DELETE protocol_history_entries ({n_ph} rows)")
        print(f"  [dry-run] DELETE payment_webhook_inbox ({n_inbox} rows)")
        print(f"  [dry-run] DELETE membership_arrears ({n_arr} rows)")
        print(f"  [dry-run] DELETE notifications ({n_notif} rows)")
        print(
            f"  [dry-run] DELETE site_settings кроме telegram* "
            f"(всего {n_site}, оставить {n_site_tg} строк с ключом telegram% )"
        )
        return

    await session.execute(delete(ProtocolHistoryEntry))
    await session.execute(delete(PaymentWebhookInbox))
    await session.execute(delete(MembershipArrear))
    await session.execute(delete(Notification))
    await session.execute(delete(SiteSetting).where(not_(SiteSetting.key.like("telegram%"))))
    print(
        f"  Удалено: protocol_entries, webhook_inbox, arrears, notifications; "
        f"site_settings кроме {n_site_tg} строк(и) с ключом telegram% ."
    )


async def collect_portal_only_user_ids(
    session: AsyncSession, role_map: dict[str, Role], exclude: set[UUID]
) -> list[UUID]:
    """Пользователи с ролью user и без staff."""
    user_rid = role_map["user"].id
    with_user = (
        await session.execute(
            select(UserRoleAssignment.user_id).where(UserRoleAssignment.role_id == user_rid)
        )
    ).scalars().all()
    out: list[UUID] = []
    for uid in with_user:
        if uid in exclude:
            continue
        if await _user_has_staff(session, uid, role_map):
            continue
        cnt = (
            await session.execute(
                select(func.count())
                .select_from(UserRoleAssignment)
                .where(UserRoleAssignment.user_id == uid)
            )
        ).scalar_one()
        if int(cnt) == 1:
            out.append(uid)
    return out


async def run(
    *,
    dry_run: bool,
    delete_portal_users_flag: bool,
    wipe_auxiliary_data: bool,
    report_path: str | None,
) -> None:
    engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        role_map = await _role_map(session)
        fallback = await _fallback_admin_id(session, role_map)

        print("=== 1. Нормализация ролей staff ===\n")
        await normalize_staff_roles(session, role_map, dry_run)

        if wipe_auxiliary_data:
            await wipe_auxiliary_business_data(session, dry_run)

        print("\n=== 2. Врачи ===\n")
        doctor_rid = role_map["doctor"].id
        doctor_uids = list(
            (
                await session.execute(
                    select(UserRoleAssignment.user_id).where(
                        UserRoleAssignment.role_id == doctor_rid
                    )
                )
            ).scalars().all()
        )
        staff_rid_set = {role_map[n].id for n in STAFF_ROLE_NAMES}

        to_delete: list[UUID] = []
        for uid in doctor_uids:
            other_roles = (
                await session.execute(
                    select(UserRoleAssignment.role_id).where(
                        UserRoleAssignment.user_id == uid,
                        UserRoleAssignment.role_id != doctor_rid,
                    )
                )
            ).scalars().all()
            has_staff = any(rid in staff_rid_set for rid in other_roles)
            if has_staff:
                u = await session.get(User, uid)
                print(f"Врач+staff {u.email}: убрать профиль врача")
                await strip_doctor_from_staff(session, uid, role_map, dry_run)
            else:
                to_delete.append(uid)

        if delete_portal_users_flag:
            print("\n=== 3. Только user (без staff) ===\n")
            portal = await collect_portal_only_user_ids(
                session, role_map, exclude={fallback}
            )
            for uid in portal:
                u = await session.get(User, uid)
                print(f"Удалить portal-only user: {u.email if u else uid}")
            to_delete.extend(portal)

        to_delete = list({u for u in to_delete if u != fallback})

        print("\n=== 4. Полное удаление пользователей ===\n")
        await delete_users_full(session, to_delete, fallback, dry_run)

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    lines = [
        "# Отчёт db_cleanup_doctors",
        f"Режим: {'DRY-RUN' if dry_run else 'EXECUTE'}",
        f"UTC: {datetime.now(UTC).isoformat()}",
        "",
        "## Учётки staff (email — пароли не сбрасывались)",
        "",
    ]
    async with factory() as session:
        role_map = await _role_map(session)
        staff_ids = {role_map[n].id for n in STAFF_ROLE_NAMES}
        rows = (
            await session.execute(
                select(User.email, Role.name)
                .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
                .join(Role, Role.id == UserRoleAssignment.role_id)
                .where(UserRoleAssignment.role_id.in_(staff_ids))
                .order_by(User.email)
            )
        ).all()
        for email, rname in rows:
            lines.append(f"- {email}  ({rname})")

    text_out = "\n".join(lines)
    print("\n" + text_out)
    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(text_out)
        print(f"\nОтчёт: {report_path}")

    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true", help="Выполнить (по умолчанию dry-run)")
    p.add_argument(
        "--wipe-auxiliary-data",
        action="store_true",
        help=(
            "Дополнительно очистить protocol_history, webhook inbox, arrears, notifications "
            "и site_settings (кроме ключей telegram*). Не трогает telegram_integrations и "
            "certificate_settings."
        ),
    )
    p.add_argument(
        "--delete-portal-users",
        action="store_true",
        help="Удалить пользователей только с ролью user (без staff)",
    )
    p.add_argument("--report", default="", help="Файл отчёта")
    args = p.parse_args()
    asyncio.run(
        run(
            dry_run=not args.execute,
            delete_portal_users_flag=args.delete_portal_users,
            wipe_auxiliary_data=args.wipe_auxiliary_data,
            report_path=args.report.strip() or None,
        )
    )


if __name__ == "__main__":
    main()
