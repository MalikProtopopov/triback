"""Shared utilities — slug generation, transliteration."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        q = select(model.id).where(col == candidate)  # type: ignore[arg-type]
        if existing_id is not None:
            q = q.where(pk != existing_id)
        result = await db.execute(q)
        if result.scalar_one_or_none() is None:
            return candidate
        counter += 1
        candidate = f"{base}-{counter}"
