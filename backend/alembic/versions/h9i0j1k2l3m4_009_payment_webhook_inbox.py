"""009 - Add payment_webhook_inbox table for reliable webhook processing

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-03-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h9i0j1k2l3m4"
down_revision: str | None = "g8h9i0j1k2l3"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_webhook_inbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_event_key", sa.String(length=512), nullable=False),
        sa.Column("raw_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("verify_error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_pwi_provider_ext",
        "payment_webhook_inbox",
        ["provider", "external_event_key"],
        unique=True,
    )
    op.create_index(
        "ix_pwi_status_next_run",
        "payment_webhook_inbox",
        ["status", "next_run_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pwi_status_next_run", table_name="payment_webhook_inbox")
    op.drop_index("ix_pwi_provider_ext", table_name="payment_webhook_inbox")
    op.drop_table("payment_webhook_inbox")
