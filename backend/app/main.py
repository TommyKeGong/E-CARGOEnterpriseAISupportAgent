"""HTTP entry point for the E-CARGO Knowledge Agent."""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.models import AcademicDocument, DocumentChunk
from app.schemas import (
    KeywordSearchResponse,
    KeywordSearchResult,
    PaperChunkPageResponse,
    PaperChunkResponse,
    PaperDetailResponse,
    PaperListItem,
    PaperListResponse,
)

app = FastAPI(
    title="E-CARGO Knowledge Agent",
    version="0.1.0",
    description="Local-first, evidence-grounded academic RAG backend.",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Return a liveness signal without contacting the database or AWS."""
    return {"status": "healthy"}


def _database_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The local document database is unavailable.",
    )


def _paper_not_found(document_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Paper '{document_id}' was not found.",
    )


def _excerpt(chunk_text: str, query: str, maximum_length: int = 400) -> str:
    """Return a bounded local excerpt centred on the case-insensitive match."""
    match_index = chunk_text.casefold().find(query.casefold())
    if match_index < 0:
        return chunk_text[:maximum_length]
    start = max(0, match_index - 120)
    end = min(len(chunk_text), start + maximum_length)
    prefix = "…" if start else ""
    suffix = "…" if end < len(chunk_text) else ""
    return f"{prefix}{chunk_text[start:end]}{suffix}"


@app.get("/api/v1/papers", response_model=PaperListResponse, tags=["papers"])
def list_papers(db: Annotated[Session, Depends(get_db_session)]) -> PaperListResponse:
    """List persisted local papers without returning source-file contents."""
    try:
        chunk_count = func.count(DocumentChunk.chunk_id).label("chunk_count")
        rows = db.execute(
            select(AcademicDocument, chunk_count)
            .outerjoin(DocumentChunk, DocumentChunk.document_id == AcademicDocument.document_id)
            .group_by(AcademicDocument.document_id)
            .order_by(AcademicDocument.source_filename)
        ).all()
    except SQLAlchemyError as error:
        raise _database_unavailable() from error

    items = [
        PaperListItem(
            document_id=document.document_id,
            source_filename=document.source_filename,
            title=document.title,
            authors=document.authors,
            publication_year=document.publication_year,
            page_count=document.page_count,
            chunk_count=count,
        )
        for document, count in rows
    ]
    return PaperListResponse(items=items, total=len(items))


@app.get("/api/v1/papers/search", response_model=KeywordSearchResponse, tags=["papers"])
def search_papers_keyword(
    q: Annotated[str, Query(min_length=1, max_length=200, description="Keyword or phrase")],
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> KeywordSearchResponse:
    """Perform bounded PostgreSQL ILIKE keyword search, not semantic retrieval."""
    try:
        rows = db.execute(
            select(DocumentChunk, AcademicDocument.source_filename)
            .join(AcademicDocument, AcademicDocument.document_id == DocumentChunk.document_id)
            .where(DocumentChunk.chunk_text.ilike(f"%{q}%"))
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
            .limit(limit)
        ).all()
    except SQLAlchemyError as error:
        raise _database_unavailable() from error

    items = [
        KeywordSearchResult(
            document_id=chunk.document_id,
            source_filename=source_filename,
            pdf_page_number=chunk.pdf_page_number,
            chunk_id=chunk.chunk_id,
            excerpt=_excerpt(chunk.chunk_text, q),
        )
        for chunk, source_filename in rows
    ]
    return KeywordSearchResponse(query=q, items=items, total=len(items))


@app.get(
    "/api/v1/papers/{document_id}/chunks",
    response_model=PaperChunkPageResponse,
    tags=["papers"],
)
def list_paper_chunks(
    document_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaperChunkPageResponse:
    """Return a page of chunks for one imported paper in stable chunk order."""
    try:
        document = db.get(AcademicDocument, document_id)
        if document is None:
            raise _paper_not_found(document_id)
        total = db.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .offset(offset)
            .limit(limit)
        ).all()
    except SQLAlchemyError as error:
        raise _database_unavailable() from error

    return PaperChunkPageResponse(
        document_id=document_id,
        items=[
            PaperChunkResponse(
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                pdf_page_number=chunk.pdf_page_number,
                chunk_text=chunk.chunk_text,
            )
            for chunk in chunks
        ],
        limit=limit,
        offset=offset,
        total=total or 0,
    )


@app.get("/api/v1/papers/{document_id}", response_model=PaperDetailResponse, tags=["papers"])
def get_paper(
    document_id: str, db: Annotated[Session, Depends(get_db_session)]
) -> PaperDetailResponse:
    """Return persisted metadata for one imported paper."""
    try:
        document = db.get(AcademicDocument, document_id)
        if document is None:
            raise _paper_not_found(document_id)
        chunk_count = db.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
    except SQLAlchemyError as error:
        raise _database_unavailable() from error

    return PaperDetailResponse(
        document_id=document.document_id,
        source_filename=document.source_filename,
        title=document.title,
        authors=document.authors,
        publication_year=document.publication_year,
        page_count=document.page_count,
        chunk_count=chunk_count or 0,
        publication_venue=document.publication_venue,
        doi=document.doi,
        rights_status=document.rights_status,
    )
