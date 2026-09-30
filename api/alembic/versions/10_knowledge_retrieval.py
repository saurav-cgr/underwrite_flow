"""Add pgvector and generated full-text search to knowledge passages."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from underwriteflow.persistence.vector import Vector


revision = "10_knowledge_retrieval"
down_revision = "09_knowledge_base"
branch_labels = None
depends_on = None


# Add vector and full-text retrieval storage and indexes.
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "knowledge_passages",
        sa.Column("embedding", Vector(768), nullable=True),
    )
    op.add_column(
        "knowledge_passages",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', "
                "coalesce(passage_key, '') || ' ' || "
                "coalesce(topic, '') || ' ' || "
                "coalesce(title, '') || ' ' || "
                "coalesce(body, ''))",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_knowledge_passages_search_vector",
        "knowledge_passages",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_knowledge_passages_embedding_hnsw",
        "knowledge_passages",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


# Remove only retrieval objects introduced by this revision.
def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_passages_embedding_hnsw",
        table_name="knowledge_passages",
    )
    op.drop_index(
        "ix_knowledge_passages_search_vector",
        table_name="knowledge_passages",
    )
    op.drop_column("knowledge_passages", "search_vector")
    op.drop_column("knowledge_passages", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
