"""Shared utilities — slug generation, transliteration."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profiles import DoctorProfile

_CYR_TO_LAT: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y",
    "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def transliterate(text: str) -> str:
    result: list[str] = []
    for ch in text.lower():
        result.append(_CYR_TO_LAT.get(ch, ch))
    return "".join(result)


def slugify(text: str) -> str:
    latin = transliterate(text)
    slug = re.sub(r"[^a-z0-9]+", "-", latin)
    return slug.strip("-")


async def generate_unique_slug(
    db: AsyncSession,
    model: Any,
    title: str,
    *,
    slug_column: str = "slug",
    existing_id: Any | None = None,
) -> str:
    """Generate a URL-safe slug from *title*, ensuring uniqueness in *model* table."""
    base = slugify(title)
    if not base:
        base = "item"

    candidate = base
    counter = 1
    col = getattr(model, slug_column)
    pk = model.id

    while True:
        q = select(model.id).where(col == candidate)
        if existing_id is not None:
            q = q.where(pk != existing_id)
        result = await db.execute(q)
        if result.scalar_one_or_none() is None:
            return candidate
        counter += 1
        candidate = f"{base}-{counter}"


async def generate_doctor_slug(
    db: AsyncSession,
    profile: DoctorProfile,
    *,
    city_name: str | None = None,
) -> str:
    """Public doctor URL slug from ФИО; if taken, append specialization and/or city, then numeric suffix."""
    parts: list[str] = []
    for p in (profile.last_name, profile.first_name, profile.middle_name):
        if p and str(p).strip():
            parts.append(str(p).strip())
    fio = " ".join(parts)
    if not fio:
        return await generate_unique_slug(db, DoctorProfile, "doctor", existing_id=profile.id)

    base = slugify(fio) or "doctor"
    spec = ""
    if profile.specialization and str(profile.specialization).strip():
        spec = slugify(str(profile.specialization).strip())
    city = ""
    if city_name and str(city_name).strip():
        city = slugify(str(city_name).strip())

    candidates: list[str] = []
    seen: set[str] = set()

    def add(c: str) -> None:
        c = c.strip("-")
        if not c or c in seen:
            return
        seen.add(c)
        candidates.append(c)

    add(base)
    if spec:
        add(f"{base}-{spec}")
    if city:
        add(f"{base}-{city}")
    if spec and city:
        add(f"{base}-{spec}-{city}")

    for cand in candidates:
        q = select(DoctorProfile.id).where(
            DoctorProfile.slug == cand,
            DoctorProfile.id != profile.id,
        )
        r = await db.execute(q)
        if r.scalar_one_or_none() is None:
            return cand

    tail_bits: list[str] = []
    if profile.specialization and str(profile.specialization).strip():
        tail_bits.append(str(profile.specialization).strip())
    if city_name and str(city_name).strip():
        tail_bits.append(str(city_name).strip())
    tail = " ".join(tail_bits)
    title = f"{fio} {tail}" if tail else fio
    return await generate_unique_slug(db, DoctorProfile, title, existing_id=profile.id)
