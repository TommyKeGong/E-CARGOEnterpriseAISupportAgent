"""Add model-scoped local and future remote embedding storage.

Revision ID: 0003_chunk_embeddings
Revises: 0002_authors_jsonb
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision = "0003_chunk_embeddings"
down_revision = "0002_authors_jsonb"
branch_labels = None
depends_on = None

LOCAL_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def upgrade() -> None:
    op.create_table(
        "chunk_embeddings",
        sa.Column("embedding_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("model_id", sa.String(length=256), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("dimension > 0", name="ck_chunk_embeddings_dimension_positive"),
        sa.CheckConstraint(
            "vector_dims(embedding) = dimension",
            name="ck_chunk_embeddings_dimension_matches_vector",
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["paper_chunks.chunk_id"]),
        sa.UniqueConstraint("chunk_id", "model_id", name="uq_chunk_embeddings_chunk_model"),
    )
    op.execute(
        "CREATE INDEX ix_chunk_embeddings_local_384_cosine ON chunk_embeddings "
        "USING hnsw ((embedding::vector(384)) vector_cosine_ops) "
        f"WHERE model_id = '{LOCAL_MODEL_ID}'"
    )


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade is intentionally disabled")
