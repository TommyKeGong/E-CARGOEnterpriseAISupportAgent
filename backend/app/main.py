"""HTTP entry point for the E-CARGO Knowledge Agent."""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.embeddings.local import (
    COSINE_DISTANCE_METRIC,
    LOCAL_MODEL_ID,
    LOCAL_MODEL_REVISION,
    get_local_encoder,
    semantic_search,
)
from app.models import AcademicDocument, DocumentChunk
from app.rag.orchestrator import GroundedRAGOrchestrator
from app.rag.providers import get_default_provider
from app.schemas import (
    AnswerCitation,
    AskRequest,
    AskResponse,
    DebugRetrievalResult,
    KeywordSearchResponse,
    KeywordSearchResult,
    PaperChunkPageResponse,
    PaperChunkResponse,
    PaperDetailResponse,
    PaperListItem,
    PaperListResponse,
    RetrievalResponse,
    SelectedEvidence,
    SemanticSearchResponse,
    SemanticSearchResult,
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


def run_grounded_rag(
    db: Session, question: str, top_k: int, debug_retrieval: bool = False
) -> AskResponse:
    """Run the offline mock-backed grounded RAG path; no remote provider is contacted."""
    result = GroundedRAGOrchestrator(provider=get_default_provider()).answer(
        db, question, get_local_encoder(), top_k=top_k, debug_retrieval=debug_retrieval
    )
    return AskResponse(
        question=result.question,
        answer=result.answer,
        status=result.status,
        provider=result.provider,
        citations=[
            AnswerCitation(
                document_id=citation.document_id,
                chunk_id=citation.chunk_id,
                source_filename=citation.source_filename,
                pdf_page_number=citation.pdf_page_number,
            )
            for citation in result.citations
        ],
        selected_evidence=[
            SelectedEvidence(
                document_id=evidence.document_id,
                chunk_id=evidence.chunk_id,
                source_filename=evidence.source_filename,
                pdf_page_number=evidence.pdf_page_number,
                chunk_text=evidence.original_chunk_text,
                similarity_score=evidence.similarity_score,
            )
            for evidence in result.selected_evidence
        ],
        debug_retrieval=(
            [
                DebugRetrievalResult(
                    document_id=decision.result.document_id,
                    chunk_id=decision.result.chunk_id,
                    source_filename=decision.result.source_filename,
                    pdf_page_number=decision.result.pdf_page_number,
                    chunk_text=decision.result.chunk_text,
                    similarity_score=decision.result.similarity_score,
                    selected=decision.selected,
                    selection_reason=decision.selection_reason,
                )
                for decision in result.debug_retrieval
            ]
            if debug_retrieval
            else None
        ),
        retrieval=RetrievalResponse(
            search_type="semantic",
            model_id=result.retrieval.model_id,
            model_revision=result.retrieval.model_revision,
            distance_metric="cosine",
            retrieved_count=result.retrieval.retrieved_count,
            selected_count=result.retrieval.selected_count,
        ),
        invalid_citation_count=result.invalid_citation_count,
    )


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
    "/api/v1/papers/semantic-search",
    response_model=SemanticSearchResponse,
    tags=["papers"],
)
def search_papers_semantic(
    q: Annotated[str, Query(min_length=1, max_length=500, description="Natural-language query")],
    db: Annotated[Session, Depends(get_db_session)],
    top_k: Annotated[int, Query(ge=1, le=20)] = 5,
    document_id: str | None = None,
) -> SemanticSearchResponse:
    """Search local 384-d embeddings with pgvector cosine distance, not answer probability."""
    try:
        if document_id is not None and db.get(AcademicDocument, document_id) is None:
            raise _paper_not_found(document_id)
        results = semantic_search(db, q, get_local_encoder(), top_k=top_k, document_id=document_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except (RuntimeError, SQLAlchemyError) as error:
        raise _database_unavailable() from error
    return SemanticSearchResponse(
        model_id=LOCAL_MODEL_ID,
        model_revision=LOCAL_MODEL_REVISION,
        distance_metric=COSINE_DISTANCE_METRIC,
        query=q,
        results=[
            SemanticSearchResult(
                document_id=result.document_id,
                source_filename=result.source_filename,
                chunk_id=result.chunk_id,
                pdf_page_number=result.pdf_page_number,
                similarity_score=result.similarity_score,
                excerpt=_excerpt(result.chunk_text, q),
            )
            for result in results
        ],
    )


@app.post("/api/v1/ask", response_model=AskResponse, tags=["rag"])
def ask_question(
    request: AskRequest, db: Annotated[Session, Depends(get_db_session)]
) -> AskResponse:
    """Return selected local evidence; the default Mock provider never claims an answer."""
    try:
        return run_grounded_rag(db, request.question, request.top_k, request.debug_retrieval)
    except (RuntimeError, SQLAlchemyError) as error:
        raise _database_unavailable() from error


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
