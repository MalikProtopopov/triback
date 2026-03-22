"""008 - Add board_role to doctor_profiles

Revision ID: g8h9i0j1k2l3
Revises: f7g8h9i0j1k2
Create Date: 2026-03-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g8h9i0j1k2l3"
down_revision: str | None = "f7g8h9i0j1k2"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    board_role = sa.Enum("pravlenie", "president", name="board_role", create_type=True)
    board_role.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "doctor_profiles",
        sa.Column("board_role", board_role, nullable=True),
    )
    op.create_index(
        "idx_doctor_profiles_board_role",
        "doctor_profiles",
        ["board_role"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_doctor_profiles_board_role", table_name="doctor_profiles")
    op.drop_column("doctor_profiles", "board_role")
    op.execute("DROP TYPE board_role")
