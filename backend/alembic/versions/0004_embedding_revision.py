"""Record embedding revisions without replacing existing vectors.

Revision ID: 0004_embedding_revision
Revises: 0003_chunk_embeddings
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_embedding_revision"
down_revision = "0003_chunk_embeddings"
branch_labels = None
depends_on = None

UNKNOWN_REVISION = "unknown"


def upgrade() -> None:
    """Keep legacy rows but make their missing provenance explicit."""
    op.add_column(
        "chunk_embeddings",
        sa.Column("model_revision", sa.String(length=64), nullable=True),
    )
    op.execute(
        "UPDATE chunk_embeddings "
        f"SET model_revision = '{UNKNOWN_REVISION}' "
        "WHERE model_revision IS NULL"
    )
    op.alter_column("chunk_embeddings", "model_revision", nullable=False)
    op.drop_constraint("uq_chunk_embeddings_chunk_model", "chunk_embeddings", type_="unique")
    op.create_unique_constraint(
        "uq_chunk_embeddings_chunk_model_revision",
        "chunk_embeddings",
        ["chunk_id", "model_id", "model_revision"],
    )
    op.create_index(
        "ix_chunk_embeddings_model_revision",
        "chunk_embeddings",
        ["model_id", "model_revision"],
    )


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade is intentionally disabled")
