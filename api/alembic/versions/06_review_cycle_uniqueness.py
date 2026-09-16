"""Enforce one persisted review per case and review cycle.

The application serializes decisions by locking the case row. This additive
constraint is the database-level safeguard behind that lock, so a second
writer can never persist two reviews for the same cycle.
"""

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


# Abort the upgrade while historical duplicate cycle reviews still exist.
def raise_on_duplicate_reviews() -> None:
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT case_id, review_cycle, count(*) FROM reviews "
                "GROUP BY case_id, review_cycle HAVING count(*) > 1"
            )
        )
        .fetchall()
    )
    if not duplicates:
        return
    found = ", ".join(
        f"case {case_id} cycle {cycle} has {count} reviews"
        for case_id, cycle, count in duplicates
    )
    raise RuntimeError(
        "cannot add uq_reviews_case_cycle because duplicate reviews exist: "
        f"{found}. Resolve these reviews before upgrading; this revision "
        "never deletes reviews."
    )


# Add the safeguard after verifying that existing rows already satisfy it.
def upgrade() -> None:
    raise_on_duplicate_reviews()
    op.create_unique_constraint(
        "uq_reviews_case_cycle",
        "reviews",
        ["case_id", "review_cycle"],
    )


# Remove only the safeguard added by this revision.
def downgrade() -> None:
    op.drop_constraint(
        "uq_reviews_case_cycle",
        "reviews",
        type_="unique",
    )
