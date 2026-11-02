"""Align paper authors with the JSONB contract.

Revision ID: 0002_authors_jsonb
Revises: 0001_academic_corpus
"""

from alembic import op

revision = "0002_authors_jsonb"
down_revision = "0001_academic_corpus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE papers ALTER COLUMN authors TYPE jsonb USING authors::jsonb")


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade is intentionally disabled")
