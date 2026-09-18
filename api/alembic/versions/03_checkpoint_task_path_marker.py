"""Mark the pinned checkpoint task-path migration as applied.

Revision ID: b2e0f1d3c4a5
Revises: a1f9d0c2e3b4
Create Date: 2026-09-10
"""

from alembic import op


revision = "b2e0f1d3c4a5"
down_revision = "a1f9d0c2e3b4"
branch_labels = None
depends_on = None


# Mark task_path DDL already present in the fresh checkpoint table definition.
def upgrade() -> None:
    op.execute(
        "INSERT INTO checkpoint_migrations (v) "
        "VALUES (9) ON CONFLICT DO NOTHING"
    )


# Remove the marker only when rolling back this compatibility revision.
def downgrade() -> None:
    op.execute("DELETE FROM checkpoint_migrations WHERE v = 9")
