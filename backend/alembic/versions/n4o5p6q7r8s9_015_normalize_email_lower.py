"""Normalize users.email to lowercase for case-insensitive auth.

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "n4o5p6q7r8s9"
down_revision = "m3n4o5p6q7r8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Refuse if case-insensitive duplicates exist — an automatic LOWER() would
    # collapse them and raise a unique-violation. Fix those accounts manually
    # (merge or rename) before running this migration.
    dupes = bind.execute(
        sa.text(
            """
            SELECT LOWER(email) AS e, COUNT(*) AS n
            FROM users
            GROUP BY LOWER(email)
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if dupes:
        rows = ", ".join(f"{r.e} ({r.n})" for r in dupes[:10])
        raise RuntimeError(
            "Cannot normalize users.email — case-insensitive duplicates exist. "
            "Resolve them manually before upgrading. Affected: " + rows
        )

    op.execute(
        "UPDATE users SET email = LOWER(email) WHERE email <> LOWER(email)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users (LOWER(email))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_users_email_lower")
