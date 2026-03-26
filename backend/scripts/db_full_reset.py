#!/usr/bin/env python3
"""Полная очистка данных PostgreSQL (все таблицы в public, кроме alembic_version).

Схема и миграции не трогаются — остаётся только история Alembic, затем можно снова
наполнять данные (роли, staff, сиды).

Не затрагивает файлы .env и Redis (сессии/кэш в Redis при необходимости сбросьте отдельно).

Usage (backend/):
  poetry run python scripts/db_full_reset.py              # dry-run: список таблиц
  poetry run python scripts/db_full_reset.py --execute    # TRUNCATE ... CASCADE
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.dirname(_script_dir)
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings  # noqa: E402

EXCLUDED_TABLES = frozenset({"alembic_version"})


async def run(*, dry_run: bool) -> None:
    engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        )
        tables = [row[0] for row in result.all()]
        to_truncate = [t for t in tables if t not in EXCLUDED_TABLES]

        if not to_truncate:
            print("Нет таблиц для очистки.")
            await engine.dispose()
            return

        print(f"Таблиц в public: {len(tables)}, к TRUNCATE: {len(to_truncate)}")
        print("Исключено:", ", ".join(sorted(EXCLUDED_TABLES)))
        for t in to_truncate:
            print(f"  - {t}")

        if dry_run:
            print("\n[dry-run] TRUNCATE не выполнялся. Запустите с --execute.")
            await session.rollback()
            await engine.dispose()
            return

        quoted = ", ".join(f'"{t}"' for t in to_truncate)
        await session.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
        await session.commit()
        print("\nГотово: все данные в перечисленных таблицах удалены (RESTART IDENTITY CASCADE).")

    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description="Полная очистка данных БД (PostgreSQL public).")
    p.add_argument(
        "--execute",
        action="store_true",
        help="Выполнить TRUNCATE (без флага — только список таблиц, dry-run).",
    )
    args = p.parse_args()
    asyncio.run(run(dry_run=not args.execute))


if __name__ == "__main__":
    main()
