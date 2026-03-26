"""Protocol history entries (admission / exclusion).

Revision ID: k1l2m3n4o5p6
Revises: j1k2l3m4n5o6
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "k1l2m3n4o5p6"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "protocol_history_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("protocol_title", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("doctor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_edited_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.CheckConstraint("year >= 2000 AND year <= 2100", name="chk_protocol_history_year"),
        sa.CheckConstraint(
            "action_type IN ('admission', 'exclusion')",
            name="chk_protocol_history_action_type",
        ),
        sa.ForeignKeyConstraint(["doctor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["last_edited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_protocol_history_doctor_user_id",
        "protocol_history_entries",
        ["doctor_user_id"],
    )
    op.create_index(
        "idx_protocol_history_action_type",
        "protocol_history_entries",
        ["action_type"],
    )
    op.create_index(
        "idx_protocol_history_created_at",
        "protocol_history_entries",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("protocol_history_entries")
