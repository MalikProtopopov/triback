"""005 - Add payments.expires_at column and 'expired' payment status

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-03-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'expired'")
    op.add_column(
        "payments",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill: set expires_at = created_at + 24h for existing pending payments
    op.execute(
        "UPDATE payments SET expires_at = created_at + interval '24 hours' "
        "WHERE expires_at IS NULL AND status = 'pending'"
    )


def downgrade() -> None:
    op.drop_column("payments", "expires_at")
