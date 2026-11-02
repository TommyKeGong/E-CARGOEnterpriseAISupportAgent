"""Academic corpus SQLAlchemy models."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AcademicDocument(Base):
    __tablename__ = "papers"
    document_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    authors: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    publication_venue: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(512), nullable=True, unique=True)
    source_filename: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    rights_status: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sections: Mapped[list["DocumentSection"]] = relationship(back_populates="document")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")
    __table_args__ = (CheckConstraint("page_count > 0", name="ck_papers_page_count_positive"),)


class DocumentSection(Base):
    __tablename__ = "paper_sections"
    section_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("papers.document_id"), nullable=False)
    heading: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    document: Mapped[AcademicDocument] = relationship(back_populates="sections")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="section")
    __table_args__ = (
        UniqueConstraint("document_id", "section_index", name="uq_paper_sections_document_index"),
    )


class DocumentChunk(Base):
    __tablename__ = "paper_chunks"
    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("papers.document_id"), nullable=False)
    section_id: Mapped[str | None] = mapped_column(
        ForeignKey("paper_sections.section_id"), nullable=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    pdf_page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    printed_page_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(512), nullable=True)
    document: Mapped[AcademicDocument] = relationship(back_populates="chunks")
    section: Mapped[DocumentSection | None] = relationship(back_populates="chunks")
    embeddings: Mapped[list["ChunkEmbedding"]] = relationship(back_populates="chunk")
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_paper_chunks_document_index"),
        CheckConstraint("chunk_index >= 0", name="ck_paper_chunks_index_nonnegative"),
        CheckConstraint("pdf_page_index >= 0", name="ck_paper_chunks_page_index_nonnegative"),
        CheckConstraint("pdf_page_number > 0", name="ck_paper_chunks_page_number_positive"),
    )


class ChunkEmbedding(Base):
    """Model-scoped vectors; never mix dimensions or model families in retrieval."""

    __tablename__ = "chunk_embeddings"
    embedding_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("paper_chunks.chunk_id"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(256), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    chunk: Mapped[DocumentChunk] = relationship(back_populates="embeddings")
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "model_id",
            "model_revision",
            name="uq_chunk_embeddings_chunk_model_revision",
        ),
        CheckConstraint("dimension > 0", name="ck_chunk_embeddings_dimension_positive"),
        CheckConstraint(
            "vector_dims(embedding) = dimension",
            name="ck_chunk_embeddings_dimension_matches_vector",
        ),
    )
