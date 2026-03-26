#!/usr/bin/env python3
"""Создание трёх учёток staff: admin, manager, accountant — по одной роли на пользователя.

Запускайте после миграций и (при необходимости) после db_full_reset.py.
Пароли и email заданы ниже — смените их на продакшене после первого входа.

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
STAFF_ACCOUNTS: list[dict[str, str]] = [
    {
        "email": "admin@triho-staff.local",
        "password": "Triho_Admin_2026!Staff",
        "role": "admin",
    },
    {
        "email": "manager@triho-staff.local",
        "password": "Triho_Manager_2026!Staff",
        "role": "manager",
    },
    {
        "email": "accountant@triho-staff.local",
        "password": "Triho_Accountant_2026!Staff",
        "role": "accountant",
    },
]

ROLES_SEED = [
    ("admin", "Администратор"),
    ("manager", "Менеджер"),
    ("accountant", "Бухгалтер"),
    ("doctor", "Врач"),
    ("user", "Пользователь"),
]


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


async def seed(*, dry_run: bool) -> None:
    engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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
    args = p.parse_args()
    asyncio.run(seed(dry_run=not args.execute))


if __name__ == "__main__":
    main()
