"""Structural citation validation against request-scoped evidence and the database."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentChunk
from app.rag.evidence import Evidence
from app.rag.providers import CitationCandidate


@dataclass(frozen=True)
class ValidCitation:
    document_id: str
    chunk_id: str
    source_filename: str
    pdf_page_number: int


@dataclass(frozen=True)
class CitationValidation:
    citations: list[ValidCitation]
    invalid_count: int


class CitationValidator:
    """Validate structural provenance; semantic support needs separate human evaluation."""

    def validate(
        self,
        session: Session,
        evidence: list[Evidence],
        candidates: list[CitationCandidate],
    ) -> CitationValidation:
        evidence_by_chunk = {item.chunk_id: item for item in evidence}
        requested_ids = {candidate.chunk_id for candidate in candidates}
        rows = session.scalars(
            select(DocumentChunk).where(DocumentChunk.chunk_id.in_(requested_ids))
        ).all()
        chunks_by_id = {chunk.chunk_id: chunk for chunk in rows}
        valid: list[ValidCitation] = []
        invalid_count = 0
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.chunk_id in seen:
                continue
            seen.add(candidate.chunk_id)
            evidence_item = evidence_by_chunk.get(candidate.chunk_id)
            database_chunk = chunks_by_id.get(candidate.chunk_id)
            if (
                evidence_item is None
                or database_chunk is None
                or candidate.document_id != evidence_item.document_id
                or candidate.document_id != database_chunk.document_id
                or candidate.pdf_page_number != evidence_item.pdf_page_number
                or candidate.pdf_page_number != database_chunk.pdf_page_number
            ):
                invalid_count += 1
                continue
            valid.append(
                ValidCitation(
                    document_id=database_chunk.document_id,
                    chunk_id=database_chunk.chunk_id,
                    source_filename=evidence_item.source_filename,
                    pdf_page_number=database_chunk.pdf_page_number,
                )
            )
        return CitationValidation(citations=valid, invalid_count=invalid_count)
