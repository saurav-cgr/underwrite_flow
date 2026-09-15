"""Add persistence and concurrency safeguards for remediation step R1.

Adds an optional document code, review-cycle and specialist metadata,
product reference-file storage metadata, applicant-scoped case idempotency,
and a partial unique index for one active version per product.
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


# Add the R1 columns, then swap global idempotency for applicant scope.
def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("document_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "cases",
        sa.Column(
            "review_cycle",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "review_cycle",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "reviews",
        sa.Column("specialist_label", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "reference_documents",
        sa.Column("content_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "reference_documents",
        sa.Column("storage_key", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "reference_documents",
        sa.Column("byte_size", sa.Integer(), nullable=True),
    )
    op.add_column(
        "reference_documents",
        sa.Column("page_count", sa.Integer(), nullable=True),
    )
    op.drop_constraint("cases_idempotency_key_key", "cases", type_="unique")
    op.create_unique_constraint(
        "uq_cases_applicant_idempotency",
        "cases",
        ["applicant_user_id", "idempotency_key"],
    )
    op.create_index(
        "uq_product_versions_one_active",
        "product_versions",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


# Remove only the safeguards added by this additive revision.
def downgrade() -> None:
    op.drop_index(
        "uq_product_versions_one_active",
        table_name="product_versions",
    )
    op.drop_constraint(
        "uq_cases_applicant_idempotency",
        "cases",
        type_="unique",
    )
    op.create_unique_constraint(
        "cases_idempotency_key_key",
        "cases",
        ["idempotency_key"],
    )
    op.drop_column("reference_documents", "page_count")
    op.drop_column("reference_documents", "byte_size")
    op.drop_column("reference_documents", "storage_key")
    op.drop_column("reference_documents", "content_type")
    op.drop_column("reviews", "specialist_label")
    op.drop_column("reviews", "review_cycle")
    op.drop_column("cases", "review_cycle")
    op.drop_column("documents", "document_code")
