"""Initial non-destructive academic corpus schema."""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision, down_revision, branch_labels, depends_on = "0001_academic_corpus", None, None, None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "papers",
        sa.Column("document_id", sa.String(32), primary_key=True),
        sa.Column("title", sa.String(1000)),
        sa.Column("authors", sa.JSON()),
        sa.Column("publication_year", sa.Integer()),
        sa.Column("publication_venue", sa.String(1000)),
        sa.Column("doi", sa.String(512), unique=True),
        sa.Column("source_filename", sa.String(1024), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("rights_status", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("page_count > 0", name="ck_papers_page_count_positive"),
    )
    op.create_table(
        "paper_sections",
        sa.Column("section_id", sa.String(48), primary_key=True),
        sa.Column(
            "document_id", sa.String(32), sa.ForeignKey("papers.document_id"), nullable=False
        ),
        sa.Column("heading", sa.String(1000)),
        sa.Column("section_index", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "document_id", "section_index", name="uq_paper_sections_document_index"
        ),
    )
    op.create_table(
        "paper_chunks",
        sa.Column("chunk_id", sa.String(64), primary_key=True),
        sa.Column(
            "document_id", sa.String(32), sa.ForeignKey("papers.document_id"), nullable=False
        ),
        sa.Column("section_id", sa.String(48), sa.ForeignKey("paper_sections.section_id")),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("pdf_page_index", sa.Integer(), nullable=False),
        sa.Column("pdf_page_number", sa.Integer(), nullable=False),
        sa.Column("printed_page_label", sa.String(128)),
        sa.Column("embedding", Vector(512)),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_paper_chunks_document_index"),
        sa.CheckConstraint("chunk_index >= 0", name="ck_paper_chunks_index_nonnegative"),
        sa.CheckConstraint("pdf_page_index >= 0", name="ck_paper_chunks_page_index_nonnegative"),
        sa.CheckConstraint("pdf_page_number > 0", name="ck_paper_chunks_page_number_positive"),
    )
    op.create_index("ix_paper_chunks_document_id", "paper_chunks", ["document_id"])


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade is intentionally disabled")
