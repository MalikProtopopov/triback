"""Membership arrears, product_type membership_arrears, doctor profile flags.

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "j1k2l3m4n5o6"
down_revision = "i0j1k2l3m4n5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$ BEGIN
                ALTER TYPE product_type ADD VALUE 'membership_arrears';
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )

    op.create_table(
        "membership_arrears",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "paid",
                "cancelled",
                "waived",
                name="arrear_status",
                native_enum=True,
                create_constraint=True,
            ),
            server_default="open",
            nullable=False,
        ),
        sa.Column("source", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("escalation_level", sa.String(length=32), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waived_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("waive_reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["waived_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_membership_arrears_user_id", "membership_arrears", ["user_id"])
    op.create_index("idx_membership_arrears_status", "membership_arrears", ["status"])
    op.create_index("idx_membership_arrears_year", "membership_arrears", ["year"])
    op.create_index(
        "uix_membership_arrears_user_year_open",
        "membership_arrears",
        ["user_id", "year"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    op.add_column(
        "payments",
        sa.Column("arrear_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_payments_arrear_id",
        "payments",
        "membership_arrears",
        ["arrear_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_payments_arrear_id", "payments", ["arrear_id"])

    op.add_column(
        "doctor_profiles",
        sa.Column(
            "entry_fee_exempt",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.add_column(
        "doctor_profiles",
        sa.Column("membership_excluded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("doctor_profiles", "membership_excluded_at")
    op.drop_column("doctor_profiles", "entry_fee_exempt")

    op.drop_index("idx_payments_arrear_id", table_name="payments")
    op.drop_constraint("fk_payments_arrear_id", "payments", type_="foreignkey")
    op.drop_column("payments", "arrear_id")

    op.drop_index("uix_membership_arrears_user_year_open", table_name="membership_arrears")
    op.drop_index("idx_membership_arrears_year", table_name="membership_arrears")
    op.drop_index("idx_membership_arrears_status", table_name="membership_arrears")
    op.drop_index("idx_membership_arrears_user_id", table_name="membership_arrears")
    op.drop_table("membership_arrears")

    op.execute(sa.text("DROP TYPE IF EXISTS arrear_status"))

    # Note: PostgreSQL cannot remove enum values from product_type easily; leave membership_arrears.
