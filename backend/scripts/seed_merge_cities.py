#!/usr/bin/env python3
"""Импорт городов в БД и слияние дубликатов.

1. Вставляет отсутствующие города из каталога (scripts/cities_catalog.py + data/cities_source_lines.txt).
2. Объединяет дубликаты в таблице cities (одинаковое нормализованное имя): профили врачей
   переносятся на каноническую запись, лишние строки удаляются.

Usage (backend/):
  poetry run python scripts/seed_merge_cities.py
  poetry run python scripts/seed_merge_cities.py --execute
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
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.utils import generate_unique_slug
from app.models.cities import City
from app.models.profiles import DoctorProfile

import cities_catalog as cat


async def insert_missing_cities(session: AsyncSession, dry_run: bool) -> int:
    names = cat.build_canonical_city_names()
    existing = (await session.execute(select(City))).scalars().all()
    by_key: dict[str, City] = {}
    for c in existing:
        k = cat.canonical_key(cat.normalize_city_name(c.name))
        if k not in by_key:
            by_key[k] = c
    n = 0
    sort_base = max((c.sort_order for c in existing), default=0)
    for i, name in enumerate(names, start=1):
        key = cat.canonical_key(name)
        if key in by_key:
            continue
        slug = await generate_unique_slug(session, City, name)
        if dry_run:
            print(f"[dry-run] INSERT city name={name!r} slug={slug!r}")
            n += 1
            continue
        sort_base += 1
        c = City(name=name, slug=slug, sort_order=sort_base, is_active=True)
        session.add(c)
        await session.flush()
        by_key[key] = c
        n += 1
    return n


async def merge_duplicate_cities(session: AsyncSession, dry_run: bool) -> int:
    """Оставить одну запись на canonical_key(name); остальные удалить после переноса city_id."""
    rows = (await session.execute(select(City).order_by(City.created_at.asc()))).scalars().all()
    groups: dict[str, list[City]] = {}
    for c in rows:
        k = cat.canonical_key(cat.normalize_city_name(c.name))
        groups.setdefault(k, []).append(c)

    merged = 0
    for key, group in groups.items():
        if len(group) <= 1:
            continue
        group.sort(key=lambda x: (len(x.name), x.sort_order, x.id))
        keeper = group[0]
        for dup in group[1:]:
            cnt = (
                await session.execute(
                    select(DoctorProfile.id).where(DoctorProfile.city_id == dup.id).limit(1)
                )
            ).scalar_one_or_none()
            if dry_run:
                print(
                    f"[dry-run] MERGE {dup.name!r} (id={dup.id}) -> {keeper.name!r} (id={keeper.id}) "
                    f"profiles={'yes' if cnt else 'no'}"
                )
            else:
                await session.execute(
                    update(DoctorProfile)
                    .where(DoctorProfile.city_id == dup.id)
                    .values(city_id=keeper.id)
                )
                await session.delete(dup)
            merged += 1
    return merged


async def run(*, dry_run: bool) -> None:
    if not cat.cities_source_path().is_file():
        print(f"Нет файла {cat.cities_source_path()}", file=sys.stderr)
        sys.exit(1)

    n_names = len(cat.build_canonical_city_names())
    print(f"Канонических названий в каталоге: {n_names}")

    engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        print("\n=== Слияние дубликатов в cities ===\n")
        mer = await merge_duplicate_cities(session, dry_run)
        print(f"Объединено дубликатов: {mer}")

        print("\n=== Вставка недостающих городов ===\n")
        ins = await insert_missing_cities(session, dry_run)
        print(f"Добавлено (или запланировано): {ins}")

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true", help="Применить (по умолчанию dry-run)")
    args = p.parse_args()
    asyncio.run(run(dry_run=not args.execute))


if __name__ == "__main__":
    main()
