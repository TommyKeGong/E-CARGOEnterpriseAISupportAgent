"""Transactional PDF persistence."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.pdf import chunk_extraction, extract_pdf
from app.models import AcademicDocument, DocumentChunk


@dataclass(frozen=True)
class IngestionResult:
    document_id: str
    source_filename: str
    page_count: int
    chunk_count: int
    status: str
    empty_text_pages: tuple[int, ...]
    replacement_character_pages: tuple[int, ...]


def document_id_for(content_hash: str) -> str:
    if len(content_hash) != 64 or any(char not in "0123456789abcdef" for char in content_hash):
        raise ValueError("content_hash must be a lowercase SHA-256 digest")
    return f"DOC-{content_hash[:20]}"


def ingest_pdf(session: Session, path: Path, *, rights_status: str = "unknown") -> IngestionResult:
    extraction = extract_pdf(path)
    existing = session.scalar(
        select(AcademicDocument).where(AcademicDocument.content_hash == extraction.content_hash)
    )
    if existing:
        return IngestionResult(
            existing.document_id,
            path.name,
            existing.page_count,
            len(existing.chunks),
            "duplicate_skipped",
            extraction.empty_text_pages,
            extraction.replacement_character_pages,
        )
    document_id, chunks = document_id_for(extraction.content_hash), chunk_extraction(extraction)
    if not chunks:
        raise ValueError(f"PDF produced no non-empty chunks: {path.name}")
    session.add(
        AcademicDocument(
            document_id=document_id,
            title=None,
            authors=None,
            publication_year=None,
            publication_venue=None,
            doi=None,
            source_filename=path.name,
            content_hash=extraction.content_hash,
            rights_status=rights_status,
            page_count=extraction.page_count,
        )
    )
    for index, (page_index, page_number, text) in enumerate(chunks):
        digest = sha256(f"{document_id}:{index}:{text}".encode()).hexdigest()[:16]
        session.add(
            DocumentChunk(
                chunk_id=f"{document_id}-C{index:04d}-{digest}",
                document_id=document_id,
                section_id=None,
                chunk_index=index,
                chunk_text=text,
                pdf_page_index=page_index,
                pdf_page_number=page_number,
                printed_page_label=None,
                embedding=None,
            )
        )
    session.flush()
    return IngestionResult(
        document_id,
        path.name,
        extraction.page_count,
        len(chunks),
        "imported",
        extraction.empty_text_pages,
        extraction.replacement_character_pages,
    )
