"""Initialize pinned LangGraph checkpoint schema markers.

Revision ID: a1f9d0c2e3b4
Revises: 8bfc3e371be5
Create Date: 2026-09-10
"""

from alembic import op


revision = "a1f9d0c2e3b4"
down_revision = "8bfc3e371be5"
branch_labels = None
depends_on = None


# Mark checkpoint DDL already included in the immutable fresh-schema baseline.
def upgrade() -> None:
    for version in range(9):
        op.execute(
            f"INSERT INTO checkpoint_migrations (v) VALUES ({version}) ON CONFLICT DO NOTHING"
        )


# Remove markers only when rolling back this additive correction.
def downgrade() -> None:
    op.execute("DELETE FROM checkpoint_migrations WHERE v BETWEEN 0 AND 8")
