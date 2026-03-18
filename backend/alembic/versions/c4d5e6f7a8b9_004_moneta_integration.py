"""004 - Moneta integration: payment_provider enum, plans.plan_type, payments.moneta_operation_id

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-03-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add 'moneta' to payment_provider enum
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction in Postgres < 12,
    # but Alembic wraps migrations in a transaction. We execute outside it.
    op.execute("ALTER TYPE payment_provider ADD VALUE IF NOT EXISTS 'moneta'")

    # 2. Add plan_type column to plans
    op.add_column(
        "plans",
        sa.Column("plan_type", sa.String(20), server_default="subscription", nullable=False),
    )
    op.create_index("idx_plans_plan_type", "plans", ["plan_type"])

    # 3. Relax CheckConstraint: duration_months >= 0 (entry_fee plans use 0)
    op.drop_constraint("chk_plans_duration", "plans", type_="check")
    op.create_check_constraint("chk_plans_duration", "plans", "duration_months >= 0")

    # 4. Add moneta_operation_id to payments
    op.add_column(
        "payments",
        sa.Column("moneta_operation_id", sa.String(255), nullable=True),
    )
    op.create_index(
        "idx_payments_moneta_op",
        "payments",
        ["moneta_operation_id"],
        postgresql_where=sa.text("moneta_operation_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_payments_moneta_op", "payments")
    op.drop_column("payments", "moneta_operation_id")

    op.drop_constraint("chk_plans_duration", "plans", type_="check")
    op.create_check_constraint("chk_plans_duration", "plans", "duration_months > 0")

    op.drop_index("idx_plans_plan_type", "plans")
    op.drop_column("plans", "plan_type")

    # Cannot remove enum value in Postgres — leave 'moneta' in place
