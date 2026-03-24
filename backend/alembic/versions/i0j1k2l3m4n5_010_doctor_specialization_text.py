"""010 - Doctor specialization as free text; drop specialization catalog tables

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "i0j1k2l3m4n5"
down_revision: str | None = "h9i0j1k2l3m4"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "doctor_profiles",
        sa.Column("specialization", sa.String(length=255), nullable=True),
    )

    op.execute(
        """
        UPDATE doctor_profiles AS dp
        SET specialization = s.name
        FROM specializations AS s
        WHERE dp.specialization_id IS NOT NULL
          AND dp.specialization_id = s.id
        """
    )

    op.execute(
        """
        UPDATE doctor_profiles AS dp
        SET specialization = sub.aggr
        FROM (
            SELECT ds.doctor_profile_id,
                   string_agg(sp.name, ', ' ORDER BY sp.name) AS aggr
            FROM doctor_specializations AS ds
            INNER JOIN specializations AS sp ON sp.id = ds.specialization_id
            GROUP BY ds.doctor_profile_id
        ) AS sub
        WHERE dp.id = sub.doctor_profile_id
          AND dp.specialization IS NULL
        """
    )

    op.drop_index("idx_doctor_specializations_spec", table_name="doctor_specializations")
    op.drop_table("doctor_specializations")

    op.drop_constraint(
        "doctor_profiles_specialization_id_fkey",
        "doctor_profiles",
        type_="foreignkey",
    )
    op.drop_index("idx_doctor_profiles_specialization", table_name="doctor_profiles")
    op.drop_column("doctor_profiles", "specialization_id")

    op.drop_index("idx_specializations_active_sort", table_name="specializations")
    op.drop_table("specializations")


def downgrade() -> None:
    op.create_table(
        "specializations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "idx_specializations_active_sort",
        "specializations",
        ["is_active", "sort_order"],
        unique=False,
    )

    op.add_column(
        "doctor_profiles",
        sa.Column("specialization_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "doctor_profiles_specialization_id_fkey",
        "doctor_profiles",
        "specializations",
        ["specialization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_doctor_profiles_specialization",
        "doctor_profiles",
        ["specialization_id"],
        unique=False,
    )

    op.create_table(
        "doctor_specializations",
        sa.Column("doctor_profile_id", sa.UUID(), nullable=False),
        sa.Column("specialization_id", sa.UUID(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["doctor_profile_id"],
            ["doctor_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["specialization_id"],
            ["specializations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("doctor_profile_id", "specialization_id"),
    )
    op.create_index(
        "idx_doctor_specializations_spec",
        "doctor_specializations",
        ["specialization_id"],
        unique=False,
    )

    op.drop_column("doctor_profiles", "specialization")
