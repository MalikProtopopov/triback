"""FAQ entries table for expert Q&A.

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m3n4o5p6q7r8"
down_revision = "l2m3n4o5p6q7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "faq_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("question_title", sa.String(500), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("author_name", sa.String(255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "original_date",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_faq_entries_is_active", "faq_entries", ["is_active"])
    op.create_index("idx_faq_entries_created_at", "faq_entries", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_faq_entries_created_at", table_name="faq_entries")
    op.drop_index("idx_faq_entries_is_active", table_name="faq_entries")
    op.drop_table("faq_entries")
