"""Media assets table for admin media library.

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "l2m3n4o5p6q7"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("s3_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("s3_key", name="uq_media_assets_s3_key"),
    )
    op.create_index("idx_media_assets_created_at", "media_assets", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_media_assets_created_at", table_name="media_assets")
    op.drop_table("media_assets")
