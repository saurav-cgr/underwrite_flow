"""Add insert-once stored case route guidance."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "11_case_guidance"
down_revision = "10_knowledge_retrieval"
branch_labels = None
depends_on = None


# Create one durable explanation slot per case review cycle and kind.
def upgrade() -> None:
    op.create_table(
        "case_guidance",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("review_cycle", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "body",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "citations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "case_id",
            "review_cycle",
            "kind",
            name="uq_case_guidance_cycle_kind",
        ),
    )


# Remove only the guidance table introduced by this revision.
def downgrade() -> None:
    op.drop_table("case_guidance")
