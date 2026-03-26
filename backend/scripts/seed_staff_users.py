#!/usr/bin/env python3
"""Создание трёх учёток staff: admin, manager, accountant — по одной роли на пользователя.

Email должны проходить валидацию API (Pydantic EmailStr): домены вроде .local / .localhost
нельзя — используйте обычный домен (ниже — example.com для примера).

Запускайте после миграций и (при необходимости) после db_full_reset.py.

Если учётки уже созданы со старыми адресами (*@triho-staff.local), выполните один раз:
  poetry run python scripts/seed_staff_users.py --execute --migrate-legacy-emails

Usage (backend/):
  poetry run python scripts/seed_staff_users.py
  poetry run python scripts/seed_staff_users.py --execute
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.dirname(_script_dir)
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.users import Role, User, UserRoleAssignment  # noqa: E402

try:
    import uuid_utils

    def _new_user_id():
        return uuid_utils.uuid7()
except ImportError:
    import uuid

    def _new_user_id():
        return uuid.uuid4()


# ---------------------------------------------------------------------------
# Учётные данные по умолчанию (только для dev/staging — смените на проде)
# ---------------------------------------------------------------------------
# Домен example.com — валиден для EmailStr; на проде замените на свой домен в скрипте.
STAFF_ACCOUNTS: list[dict[str, str]] = [
    {
        "email": "triho-admin@example.com",
        "password": "Triho_Admin_2026!Staff",
        "role": "admin",
    },
    {
        "email": "triho-manager@example.com",
        "password": "Triho_Manager_2026!Staff",
        "role": "manager",
    },
    {
        "email": "triho-accountant@example.com",
        "password": "Triho_Accountant_2026!Staff",
        "role": "accountant",
    },
]

# Старые адреса из первого сида (невалидны для логина) → новые
LEGACY_EMAIL_MAP: dict[str, str] = {
    "admin@triho-staff.local": "triho-admin@example.com",
    "manager@triho-staff.local": "triho-manager@example.com",
    "accountant@triho-staff.local": "triho-accountant@example.com",
}

ROLES_SEED = [
    ("admin", "Администратор"),
    ("manager", "Менеджер"),
    ("accountant", "Бухгалтер"),
    ("doctor", "Врач"),
    ("user", "Пользователь"),
]


async def migrate_legacy_emails(session: AsyncSession, dry_run: bool) -> int:
    """Переименовать *@triho-staff.local → адреса из STAFF_ACCOUNTS (валидны для EmailStr)."""
    changed = 0
    for old_email, new_email in LEGACY_EMAIL_MAP.items():
        user = (await session.execute(select(User).where(User.email == old_email))).scalar_one_or_none()
        if not user:
            continue
        other = (
            await session.execute(
                select(User.id).where(User.email == new_email, User.id != user.id)
            )
        ).scalar_one_or_none()
        if other:
            print(
                f"Пропуск: {new_email!r} уже занят другим пользователем, "
                f"не трогаем {old_email!r}"
            )
            continue
        if dry_run:
            print(f"[dry-run] UPDATE users SET email={new_email!r} WHERE email={old_email!r}")
        else:
            user.email = new_email
            print(f"Email обновлён: {old_email!r} → {new_email!r}")
        changed += 1
    return changed


async def ensure_roles(session: AsyncSession) -> dict[str, Role]:
    out: dict[str, Role] = {}
    for name, title in ROLES_SEED:
        r = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
        if r is None:
            r = Role(name=name, title=title)
            session.add(r)
            await session.flush()
        out[name] = r
    return out


async def seed(*, dry_run: bool, migrate_legacy: bool) -> None:
    engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    if migrate_legacy:
        print("=== Миграция старых email (.local → валидные) ===\n")
        async with factory() as session:
            await migrate_legacy_emails(session, dry_run)
            if dry_run:
                await session.rollback()
            else:
                await session.commit()
        print()

    print("Планируемые учётки:")
    for a in STAFF_ACCOUNTS:
        print(f"  {a['role']:<12} {a['email']!r}  (пароль задан в скрипте)")

    now = datetime.now(UTC)
    created = 0
    skipped = 0

    async with factory() as session:
        roles_map = await ensure_roles(session)
        if dry_run:
            print("\n[dry-run] Роли и пользователи не записывались.")
            await session.rollback()
            await engine.dispose()
            return

        for acc in STAFF_ACCOUNTS:
            email = acc["email"]
            password = acc["password"]
            role_name = acc["role"]
            if role_name not in roles_map:
                raise RuntimeError(f"Неизвестная роль: {role_name}")

            exists = (
                await session.execute(select(User.id).where(User.email == email))
            ).scalar_one_or_none()
            if exists:
                print(f"Пропуск — пользователь уже есть: {email}")
                skipped += 1
                continue

            user = User(
                id=_new_user_id(),
                email=email,
                password_hash=hash_password(password),
                is_active=True,
                email_verified_at=now,
            )
            session.add(user)
            await session.flush()

            session.add(
                UserRoleAssignment(
                    user_id=user.id,
                    role_id=roles_map[role_name].id,
                )
            )
            created += 1
            print(f"Создан: {email} → роль {role_name}")

        await session.commit()

    print(f"\nИтого: создано {created}, пропущено {skipped}.")
    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description="Засев учёток admin / manager / accountant.")
    p.add_argument(
        "--execute",
        action="store_true",
        help="Записать в БД (без флага — dry-run).",
    )
    p.add_argument(
        "--migrate-legacy-emails",
        action="store_true",
        help="Обновить в БД старые адреса *@triho-staff.local на новые (example.com).",
    )
    args = p.parse_args()
    asyncio.run(
        seed(
            dry_run=not args.execute,
            migrate_legacy=args.migrate_legacy_emails,
        )
    )


if __name__ == "__main__":
    main()
