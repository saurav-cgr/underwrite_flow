"""Add shared underwriter case question history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "12_case_questions"
down_revision = "11_case_guidance"
branch_labels = None
depends_on = None


# Create one stored row per underwriter question and cited answer.
def upgrade() -> None:
    op.create_table(
        "case_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("asked_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("covered", sa.Boolean(), nullable=False),
        sa.Column(
            "citations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(question) BETWEEN 1 AND 1000",
            name="ck_case_questions_question_length",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["asked_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_case_questions_case_created",
        "case_questions",
        ["case_id", "created_at"],
    )


# Remove only the question table introduced by this revision.
def downgrade() -> None:
    op.drop_index(
        "ix_case_questions_case_created", table_name="case_questions"
    )
    op.drop_table("case_questions")
