"""Add the persisted case journey type.

Revision 08 adds a non-null ``cases.journey_type`` column that defaults and
backfills to ``new_business``, and enforces a two-value check constraint.
Every existing case therefore reads as new business, which preserves its
prior behavior exactly.

Revision ID: 08
Revises: 07
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "08"
down_revision = "07"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ck_cases_journey_type"


# Add and backfill journey_type, then constrain it to the two known values.
def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column(
            "journey_type",
            sa.String(length=32),
            nullable=False,
            server_default="new_business",
        ),
    )
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "cases",
        "journey_type IN ('new_business', 'renewal')",
    )


# Remove only the constraint and column this revision introduces.
def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "cases", type_="check")
    op.drop_column("cases", "journey_type")
