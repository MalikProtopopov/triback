"""002 - fill doctor_profiles.slug and make NOT NULL

Revision ID: a1b2c3d4e5f6
Revises: 42fa92c6dc7c
Create Date: 2026-03-14
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "42fa92c6dc7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CYR_TO_LAT: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _slugify(text: str) -> str:
    result = []
    for ch in text.lower():
        result.append(_CYR_TO_LAT.get(ch, ch))
    latin = "".join(result)
    slug = re.sub(r"[^a-z0-9]+", "-", latin).strip("-")
    return slug or "doctor"


def upgrade() -> None:
    conn = op.get_bind()

    rows = conn.execute(
        sa.text(
            "SELECT id, last_name, first_name FROM doctor_profiles WHERE slug IS NULL"
        )
    ).fetchall()

    existing_slugs: set[str] = set()
    for row in conn.execute(
        sa.text("SELECT slug FROM doctor_profiles WHERE slug IS NOT NULL")
    ).fetchall():
        existing_slugs.add(row[0])

    for row in rows:
        profile_id, last_name, first_name = row[0], row[1] or "doctor", row[2] or ""
        base = _slugify(f"{last_name} {first_name}".strip())
        candidate = base
        counter = 1
        while candidate in existing_slugs:
            counter += 1
            candidate = f"{base}-{counter}"
        existing_slugs.add(candidate)
        conn.execute(
            sa.text("UPDATE doctor_profiles SET slug = :slug WHERE id = :id"),
            {"slug": candidate, "id": profile_id},
        )

    op.drop_index("uix_doctor_profiles_slug", table_name="doctor_profiles")

    op.alter_column(
        "doctor_profiles",
        "slug",
        existing_type=sa.String(255),
        nullable=False,
    )

    op.create_unique_constraint(
        "uix_doctor_profiles_slug", "doctor_profiles", ["slug"]
    )


def downgrade() -> None:
    op.drop_constraint("uix_doctor_profiles_slug", "doctor_profiles", type_="unique")

    op.alter_column(
        "doctor_profiles",
        "slug",
        existing_type=sa.String(255),
        nullable=True,
    )

    op.create_index(
        "uix_doctor_profiles_slug",
        "doctor_profiles",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("slug IS NOT NULL"),
    )
