"""006 - Create certificate_settings table

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-03-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "certificate_settings",
        sa.Column("id", sa.Integer(), primary_key=True, default=1),
        sa.Column("president_full_name", sa.String(255), nullable=True),
        sa.Column("president_title", sa.String(255), nullable=True),
        sa.Column("organization_full_name", sa.Text(), nullable=True),
        sa.Column("organization_short_name", sa.String(255), nullable=True),
        sa.Column("certificate_member_text", sa.Text(), nullable=True),
        sa.Column("logo_s3_key", sa.String(500), nullable=True),
        sa.Column("stamp_s3_key", sa.String(500), nullable=True),
        sa.Column("signature_s3_key", sa.String(500), nullable=True),
        sa.Column("background_s3_key", sa.String(500), nullable=True),
        sa.Column(
            "certificate_number_prefix",
            sa.String(20),
            server_default="TRICH",
            nullable=False,
        ),
        sa.Column("validity_text_template", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.execute(
        """
        INSERT INTO certificate_settings (id, president_full_name, president_title,
            organization_full_name, organization_short_name, certificate_member_text,
            certificate_number_prefix, validity_text_template)
        VALUES (1,
            'Гаджигороева Аида Гусейхановна',
            'Президент д.м.н.',
            'Межрегиональная общественная организация трихологов и специалистов в области исследования волос "Профессиональное общество трихологов"',
            'Профессиональное общество трихологов',
            'является действительным членом Межрегиональной общественной организации трихологов и специалистов в области исследования волос "Профессиональное общество трихологов"',
            'TRICH',
            'Действителен с {year} г.')
        """
    )


def downgrade() -> None:
    op.drop_table("certificate_settings")
