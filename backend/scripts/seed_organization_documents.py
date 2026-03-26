#!/usr/bin/env python3
"""Засев трёх документов организации из docs/seed/*.rtf в таблицу organization_documents.

Содержимое файлов кладётся в поле content (RTF как текст). При повторном запуске записи
обновляются по slug (slug строится из названия).

Usage (из каталога backend):
  poetry run python scripts/seed_organization_documents.py
  poetry run python scripts/seed_organization_documents.py --execute
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.dirname(_script_dir)
if _backend not in sys.path:
    sys.path.insert(0, _backend)
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.utils import slugify
from app.models.content import OrganizationDocument
from app.models.users import Role, User, UserRoleAssignment

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = REPO_ROOT / "docs" / "seed"

# Три файла из docs/seed (название для UI + порядок сортировки)
ORG_DOCUMENTS: list[dict[str, str | int]] = [
    {"file": "Отказ от услуги.rtf", "title": "Отказ от услуги", "sort_order": 0},
    {
        "file": "Положение о членстве в обществе .rtf",
        "title": "Положение о членстве в обществе",
        "sort_order": 1,
    },
    {"file": "Условия возврата товара.rtf", "title": "Условия возврата товара", "sort_order": 2},
]


def _read_rtf_text(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1251", errors="replace")


async def _first_admin_id(session: AsyncSession) -> UUID:
    row = (
        await session.execute(
            select(User.id)
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(Role.name == "admin")
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise SystemExit(
            "Нет пользователя с ролью admin. Создайте: poetry run python scripts/create_admin.py"
        )
    return row


async def seed(*, dry_run: bool) -> None:
    engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    missing: list[str] = []
    for item in ORG_DOCUMENTS:
        p = SEED_DIR / str(item["file"])
        if not p.is_file():
            missing.append(str(p))
    if missing:
        raise SystemExit("Не найдены файлы:\n" + "\n".join(missing))

    async with factory() as session:
        admin_id = await _first_admin_id(session)
        for item in ORG_DOCUMENTS:
            path = SEED_DIR / str(item["file"])
            title = str(item["title"])
            sort_order = int(item["sort_order"])
            slug = slugify(title)
            body = _read_rtf_text(path)

            existing = (
                await session.execute(
                    select(OrganizationDocument).where(OrganizationDocument.slug == slug)
                )
            ).scalar_one_or_none()

            if existing:
                if dry_run:
                    print(f"[dry-run] UPDATE organization_documents slug={slug!r} title={title!r}")
                else:
                    existing.title = title
                    existing.content = body
                    existing.sort_order = sort_order
                    existing.is_active = True
                    existing.updated_by = admin_id
            else:
                if dry_run:
                    print(f"[dry-run] INSERT organization_documents slug={slug!r} title={title!r}")
                else:
                    session.add(
                        OrganizationDocument(
                            title=title,
                            slug=slug,
                            content=body,
                            file_url=None,
                            sort_order=sort_order,
                            is_active=True,
                            updated_by=admin_id,
                        )
                    )

        if dry_run:
            await session.rollback()
        else:
            await session.commit()
            print(f"Готово: {len(ORG_DOCUMENTS)} документ(ов) в organization_documents.")

    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--execute",
        action="store_true",
        help="Записать в БД (по умолчанию dry-run)",
    )
    args = p.parse_args()
    asyncio.run(seed(dry_run=not args.execute))


if __name__ == "__main__":
    main()
