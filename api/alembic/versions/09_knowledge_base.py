"""Add the versioned guideline store and case knowledge pins."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "09_knowledge_base"
down_revision = "08"
branch_labels = None
depends_on = None

ZERO_UUID = "00000000-0000-0000-0000-000000000000"


# Create the additive knowledge tables and their active-version indexes.
def upgrade() -> None:
    op.create_table(
        "knowledge_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "source", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "validation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(
            ["activated_by_user_id"], ["users.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "knowledge_passages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("passage_key", sa.String(length=200), nullable=False),
        sa.Column("product_code", sa.String(length=100), nullable=True),
        sa.Column(
            "product_lines",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column(
            "topic_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "suggested_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "limits",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "thresholds",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("age_min", sa.Integer(), nullable=True),
        sa.Column("age_max", sa.Integer(), nullable=True),
        sa.Column("sum_assured_min", sa.Numeric(), nullable=True),
        sa.Column("sum_assured_max", sa.Numeric(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("source_locator", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["version_id"], ["knowledge_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id",
            "passage_key",
            name="uq_knowledge_passages_version_key",
        ),
    )
    op.create_table(
        "case_knowledge_pins",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("guideline_version_id", sa.Uuid(), nullable=True),
        sa.Column("regulation_version_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(
            ["guideline_version_id"], ["knowledge_versions.id"]
        ),
        sa.ForeignKeyConstraint(
            ["regulation_version_id"], ["knowledge_versions.id"]
        ),
        sa.PrimaryKeyConstraint("case_id"),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_knowledge_versions_identity "
        "ON knowledge_versions "
        "(scope, coalesce(product_id, '" + ZERO_UUID + "'::uuid), version)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_knowledge_versions_one_active "
        "ON knowledge_versions "
        "(scope, coalesce(product_id, '" + ZERO_UUID + "'::uuid)) "
        "WHERE status = 'active'"
    )


# Remove only the tables and indexes introduced by this revision.
def downgrade() -> None:
    op.drop_index(
        "uq_knowledge_versions_one_active",
        table_name="knowledge_versions",
    )
    op.drop_index(
        "uq_knowledge_versions_identity",
        table_name="knowledge_versions",
    )
    op.drop_table("case_knowledge_pins")
    op.drop_table("knowledge_passages")
    op.drop_table("knowledge_versions")
