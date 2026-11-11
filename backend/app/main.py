"""HTTP entry point for the E-CARGO Knowledge Agent."""

import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Query, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.embeddings.local import (
    COSINE_DISTANCE_METRIC,
    LOCAL_MODEL_ID,
    LOCAL_MODEL_REVISION,
    generate_local_embeddings,
    get_local_encoder,
    semantic_search,
)
from app.ingestion.pdf import PDFIngestionError
from app.ingestion.service import ingest_pdf
from app.models import AcademicDocument, ChunkEmbedding, DocumentChunk, DocumentSection
from app.rag.agent import AgentLimits, BoundedResearchAgent, get_default_agent_provider
from app.rag.orchestrator import GroundedRAGOrchestrator
from app.rag.providers import get_default_provider
from app.research_tools import ResearchToolNotFoundError, ResearchTools
from app.schemas import (
    AgentAskRequest,
    AgentAskResponse,
    AgentTraceResponse,
    AnswerCitation,
    AskRequest,
    AskResponse,
    DebugRetrievalResult,
    DocumentChunkPageResponse,
    DocumentDeleteResponse,
    DocumentDetailResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentUploadResponse,
    EvidenceResponse,
    KeywordSearchResponse,
    KeywordSearchResult,
    PaperChunkPageResponse,
    PaperChunkResponse,
    PaperDetailResponse,
    PaperListItem,
    PaperListResponse,
    ResearchPageContext,
    RetrievalResponse,
    SemanticSearchResponse,
    SemanticSearchResult,
)

UPLOAD_CHUNK_BYTES = 64 * 1024
DEFAULT_UPLOAD_MAX_BYTES = 25 * 1024 * 1024

app = FastAPI(
    title="E-CARGO Knowledge Agent",
    version="0.1.0",
    description="Local-first, evidence-grounded academic RAG backend.",
)


def _frontend_origins() -> list[str]:
    """Return explicit local development origins; never reflect arbitrary origins."""
    configured = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Return a liveness signal without contacting the database or AWS."""
    return {"status": "healthy"}


@app.post(
    "/api/v1/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Authorised PDF document")],
    db: Annotated[Session, Depends(get_db_session)],
    response: Response,
) -> DocumentUploadResponse:
    """Validate, ingest, and embed one PDF in a single database transaction."""
    temporary_path: Path | None = None
    try:
        temporary_path, filename = await _stage_pdf_upload(file)
        with db.begin():
            ingestion = ingest_pdf(db, temporary_path, source_filename=filename)
            if ingestion.status == "imported":
                embedding_run = generate_local_embeddings(
                    db, get_local_encoder(), document_id=ingestion.document_id
                )
                if embedding_run.failed or embedding_run.processed != ingestion.chunk_count:
                    raise RuntimeError("Document embedding generation did not complete.")
        document = db.get(AcademicDocument, ingestion.document_id)
        if document is None:
            raise RuntimeError("Document was not available after ingestion.")
        upload_response = DocumentUploadResponse(
            **_document_detail(db, document).model_dump(), ingestion_status=ingestion.status
        )
        if ingestion.status == "duplicate_skipped":
            response.status_code = status.HTTP_200_OK
        return upload_response
    except HTTPException:
        raise
    except (PDFIngestionError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="PDF ingestion failed validation.",
        ) from error
    except SQLAlchemyError as error:
        raise _database_unavailable() from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document ingestion could not complete.",
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@app.get("/api/v1/documents", response_model=DocumentListResponse, tags=["documents"])
def list_documents(
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    """Return a paginated local index without exposing source-file paths."""
    try:
        chunk_count = func.count(DocumentChunk.chunk_id).label("chunk_count")
        rows = db.execute(
            select(AcademicDocument, chunk_count)
            .outerjoin(DocumentChunk, DocumentChunk.document_id == AcademicDocument.document_id)
            .group_by(AcademicDocument.document_id)
            .order_by(AcademicDocument.created_at, AcademicDocument.document_id)
            .offset(offset)
            .limit(limit)
        ).all()
        total = db.scalar(select(func.count()).select_from(AcademicDocument)) or 0
    except SQLAlchemyError as error:
        raise _database_unavailable() from error
    return DocumentListResponse(
        items=[
            DocumentListItem(
                document_id=document.document_id,
                source_filename=document.source_filename,
                title=document.title,
                authors=document.authors,
                page_count=document.page_count,
                chunk_count=count,
                created_at=document.created_at,
            )
            for document, count in rows
        ],
        limit=limit,
        offset=offset,
        total=total,
    )


@app.get(
    "/api/v1/documents/{document_id}",
    response_model=DocumentDetailResponse,
    tags=["documents"],
)
def get_document(
    document_id: str, db: Annotated[Session, Depends(get_db_session)]
) -> DocumentDetailResponse:
    """Return document metadata and local embedding-index status."""
    try:
        document = db.get(AcademicDocument, document_id)
        if document is None:
            raise _document_not_found(document_id)
        return _document_detail(db, document)
    except SQLAlchemyError as error:
        raise _database_unavailable() from error


@app.get(
    "/api/v1/documents/{document_id}/chunks",
    response_model=DocumentChunkPageResponse,
    tags=["documents"],
)
def list_document_chunks(
    document_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    pdf_page_number: Annotated[int | None, Query(ge=1)] = None,
) -> DocumentChunkPageResponse:
    """Inspect one document's chunks, optionally restricted to a physical PDF page."""
    try:
        if db.get(AcademicDocument, document_id) is None:
            raise _document_not_found(document_id)
        statement = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        if pdf_page_number is not None:
            statement = statement.where(DocumentChunk.pdf_page_number == pdf_page_number)
        total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        chunks = db.scalars(
            statement.order_by(DocumentChunk.chunk_index).offset(offset).limit(limit)
        ).all()
    except SQLAlchemyError as error:
        raise _database_unavailable() from error
    return DocumentChunkPageResponse(
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
        total=total,
    )


@app.get(
    "/api/v1/documents/{document_id}/pages/{pdf_page_number}/context",
    response_model=ResearchPageContext,
    tags=["documents"],
)
def get_document_page_context(
    document_id: str,
    pdf_page_number: int,
    db: Annotated[Session, Depends(get_db_session)],
) -> ResearchPageContext:
    """Return indexed text for one physical PDF page, never reconstructed source content."""
    try:
        return ResearchTools(db, get_local_encoder()).get_page_context(document_id, pdf_page_number)
    except ResearchToolNotFoundError as error:
        raise _document_not_found(document_id) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except (RuntimeError, SQLAlchemyError) as error:
        raise _database_unavailable() from error


@app.delete(
    "/api/v1/documents/{document_id}",
    response_model=DocumentDeleteResponse,
    tags=["documents"],
)
def delete_document(
    document_id: str, db: Annotated[Session, Depends(get_db_session)]
) -> DocumentDeleteResponse:
    """Delete exactly one document and dependent chunks/embeddings transactionally."""
    try:
        with db.begin():
            document = db.get(AcademicDocument, document_id)
            if document is None:
                raise _document_not_found(document_id)
            chunk_ids = select(DocumentChunk.chunk_id).where(
                DocumentChunk.document_id == document_id
            )
            db.execute(delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id.in_(chunk_ids)))
            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
            db.execute(delete(DocumentSection).where(DocumentSection.document_id == document_id))
            db.delete(document)
        return DocumentDeleteResponse(document_id=document_id, status="deleted")
    except SQLAlchemyError as error:
        raise _database_unavailable() from error


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


def _document_not_found(document_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document '{document_id}' was not found.",
    )


def _upload_size_limit() -> int:
    try:
        limit = int(os.getenv("DOCUMENT_UPLOAD_MAX_BYTES", str(DEFAULT_UPLOAD_MAX_BYTES)))
    except ValueError as error:
        raise RuntimeError("DOCUMENT_UPLOAD_MAX_BYTES must be an integer.") from error
    if limit < 1:
        raise RuntimeError("DOCUMENT_UPLOAD_MAX_BYTES must be positive.")
    return limit


def _safe_upload_filename(filename: str | None) -> str:
    if not filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Upload filename must be a plain PDF filename.",
        )
    if len(filename) > 255 or Path(filename).suffix.casefold() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads are accepted.",
        )
    return filename


async def _stage_pdf_upload(upload: UploadFile) -> tuple[Path, str]:
    """Copy a bounded upload to an OS temporary file without retaining user-controlled paths."""
    filename = _safe_upload_filename(upload.filename)
    if upload.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload content type must be application/pdf.",
        )
    limit, total = _upload_size_limit(), 0
    temporary = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    path = Path(temporary.name)
    try:
        while chunk := await upload.read(UPLOAD_CHUNK_BYTES):
            total += len(chunk)
            if total > limit:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="PDF upload exceeds the configured size limit.",
                )
            temporary.write(chunk)
        temporary.close()
        with path.open("rb") as staged_file:
            header = staged_file.read(5)
        if total == 0 or not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Uploaded file is not a valid non-empty PDF.",
            )
        return path, filename
    except Exception:
        temporary.close()
        path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def _document_detail(db: Session, document: AcademicDocument) -> DocumentDetailResponse:
    chunk_count = (
        db.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document.document_id)
        )
        or 0
    )
    embedding_count = (
        db.scalar(
            select(func.count())
            .select_from(ChunkEmbedding)
            .join(DocumentChunk, DocumentChunk.chunk_id == ChunkEmbedding.chunk_id)
            .where(DocumentChunk.document_id == document.document_id)
            .where(ChunkEmbedding.model_id == LOCAL_MODEL_ID)
            .where(ChunkEmbedding.model_revision == LOCAL_MODEL_REVISION)
        )
        or 0
    )
    return DocumentDetailResponse(
        document_id=document.document_id,
        source_filename=document.source_filename,
        title=document.title,
        authors=document.authors,
        page_count=document.page_count,
        chunk_count=chunk_count,
        created_at=document.created_at,
        publication_year=document.publication_year,
        publication_venue=document.publication_venue,
        doi=document.doi,
        rights_status=document.rights_status,
        indexing_status="indexed" if embedding_count == chunk_count else "indexing_incomplete",
        embedding_count=embedding_count,
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
        evidence=[
            EvidenceResponse(
                document_id=evidence.document_id,
                chunk_id=evidence.chunk_id,
                source_filename=evidence.source_filename,
                pdf_page_number=evidence.pdf_page_number,
                text=evidence.original_chunk_text,
                similarity_score=evidence.similarity_score,
                selected=True,
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
                    text=decision.result.chunk_text,
                    similarity_score=decision.result.similarity_score,
                    selected=decision.selected,
                    rank=rank,
                    selection_reason=decision.selection_reason,
                )
                for rank, decision in enumerate(result.debug_retrieval, start=1)
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


@app.post("/api/v1/agent/ask", response_model=AgentAskResponse, tags=["agent"])
def ask_research_agent(
    request: AgentAskRequest, db: Annotated[Session, Depends(get_db_session)]
) -> AgentAskResponse:
    """Run the bounded fixed-tool research agent; no model-generated code is ever executed."""
    try:
        limits = AgentLimits.from_environment(request.max_tool_calls)
        result = BoundedResearchAgent(provider=get_default_agent_provider()).answer(
            db, request.question, get_local_encoder(), limits
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except (RuntimeError, SQLAlchemyError) as error:
        raise _database_unavailable() from error
    return AgentAskResponse(
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
        evidence=[
            EvidenceResponse(
                document_id=item.document_id,
                chunk_id=item.chunk_id,
                source_filename=item.source_filename,
                pdf_page_number=item.pdf_page_number,
                text=item.chunk_text,
                similarity_score=item.similarity_score,
            )
            for item in result.evidence
        ],
        tool_call_count=result.tool_call_count,
        execution_time_ms=result.execution_time_ms,
        invalid_citation_count=result.invalid_citation_count,
        debug_trace=(
            [
                AgentTraceResponse(
                    step=item.step,
                    event=item.event,
                    tool_name=item.tool_name,
                    result_item_count=item.result_item_count,
                    message=item.message,
                )
                for item in result.trace
            ]
            if request.debug_trace
            else None
        ),
    )


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
