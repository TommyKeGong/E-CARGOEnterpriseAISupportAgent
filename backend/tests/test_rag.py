"""Offline tests for grounded RAG orchestration and citation validation."""

import os
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

import app.main as main_module
from app.db import get_db_session
from app.embeddings.local import SemanticResult
from app.main import app
from app.models import AcademicDocument, DocumentChunk
from app.rag.citations import CitationValidator
from app.rag.evidence import Evidence, EvidenceSelector
from app.rag.orchestrator import GroundedRAGOrchestrator
from app.rag.providers import (
    CitationCandidate,
    MockLLMProvider,
    ProviderOutput,
    ProviderTimeoutError,
)
from app.schemas import AskResponse, RetrievalResponse


@pytest.fixture()
def database_session() -> Generator[Session, None, None]:
    from app.db import create_database_engine

    database_url = os.environ.get("DATABASE_URL")
    if database_url is None:
        pytest.skip("DATABASE_URL required for PostgreSQL integration tests")
    engine = create_database_engine(database_url)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()


def _add_chunk(session: Session, document_id: str = "TEST-RAG") -> DocumentChunk:
    session.add(
        AcademicDocument(
            document_id=document_id,
            title=None,
            authors=None,
            publication_year=None,
            publication_venue=None,
            doi=None,
            source_filename="test-rag.pdf",
            content_hash=(document_id.lower() * 64)[:64],
            rights_status="unknown",
            page_count=1,
        )
    )
    chunk = DocumentChunk(
        chunk_id=f"{document_id}-C0000",
        document_id=document_id,
        section_id=None,
        chunk_index=0,
        chunk_text="E-CARGO assigns agents to roles within an environment.",
        pdf_page_index=0,
        pdf_page_number=1,
        printed_page_label=None,
    )
    session.add(chunk)
    session.flush()
    return chunk


def _result(chunk: DocumentChunk, score: float = 0.8) -> SemanticResult:
    return SemanticResult(
        document_id=chunk.document_id,
        source_filename="test-rag.pdf",
        chunk_id=chunk.chunk_id,
        pdf_page_number=chunk.pdf_page_number,
        chunk_text=chunk.chunk_text,
        similarity_score=score,
    )


def test_evidence_selection_is_bounded_and_deduplicated(database_session: Session) -> None:
    chunk = _add_chunk(database_session, "TEST-RAG-EVIDENCE")
    duplicate = _result(chunk)
    selected = EvidenceSelector(max_evidence=3, max_total_characters=100).select(
        [_result(chunk), duplicate]
    )

    assert len(selected) == 1
    assert selected[0].chunk_id == chunk.chunk_id
    assert len(selected[0].chunk_text) <= 100
    assert selected[0].original_chunk_text == chunk.chunk_text


def test_evidence_selection_reports_reasons_for_unselected_candidates(
    database_session: Session,
) -> None:
    chunk = _add_chunk(database_session, "TEST-RAG-DECISIONS")
    decisions = (
        EvidenceSelector(max_evidence=1)
        .evaluate([_result(chunk), _result(chunk), _result(chunk, 0.1)])
        .decisions
    )

    assert [decision.selection_reason for decision in decisions] == [
        "selected",
        "duplicate_chunk_text",
        "below_minimum_similarity",
    ]


def test_citation_validator_rejects_hallucinated_or_unretrieved_citations(
    database_session: Session,
) -> None:
    chunk = _add_chunk(database_session, "TEST-RAG-CITATION")
    evidence = [
        Evidence(
            document_id=chunk.document_id,
            source_filename="test-rag.pdf",
            chunk_id=chunk.chunk_id,
            pdf_page_number=1,
            chunk_text=chunk.chunk_text,
            similarity_score=0.8,
        )
    ]
    validation = CitationValidator().validate(
        database_session,
        evidence,
        [
            CitationCandidate(chunk.document_id, chunk.chunk_id, 1),
            CitationCandidate("invented-document", "invented-chunk", 99),
        ],
    )

    assert [citation.chunk_id for citation in validation.citations] == [chunk.chunk_id]
    assert validation.invalid_count == 1


def test_orchestrator_handles_no_results_unsupported_and_provider_failures(
    database_session: Session,
) -> None:
    no_results = GroundedRAGOrchestrator(
        provider=MockLLMProvider(), retriever=lambda *_args, **_kwargs: []
    ).answer(database_session, "Unsupported question", object(), top_k=5)
    assert no_results.status == "insufficient_evidence"

    chunk = _add_chunk(database_session, "TEST-RAG-UNSUPPORTED")
    low_score = GroundedRAGOrchestrator(
        provider=MockLLMProvider(), retriever=lambda *_args, **_kwargs: [_result(chunk, 0.1)]
    ).answer(database_session, "Unsupported question", object(), top_k=5)
    assert low_score.status == "insufficient_evidence"

    class TimeoutProvider:
        provider_name = "timeout-test"

        def generate(self, question: str, evidence: list[Evidence]) -> ProviderOutput:
            raise ProviderTimeoutError("timed out")

    timeout = GroundedRAGOrchestrator(
        provider=TimeoutProvider(), retriever=lambda *_args, **_kwargs: [_result(chunk)]
    ).answer(database_session, "Question", object(), top_k=5)
    assert timeout.status == "provider_error"
    assert timeout.provider == "timeout-test"


def test_orchestrator_returns_only_valid_mock_citations(database_session: Session) -> None:
    chunk = _add_chunk(database_session, "TEST-RAG-ANSWER")
    result = GroundedRAGOrchestrator(
        provider=MockLLMProvider(), retriever=lambda *_args, **_kwargs: [_result(chunk)]
    ).answer(database_session, "What is E-CARGO?", object(), top_k=5)

    assert result.status == "evidence_retrieved"
    assert result.provider == "mock"
    assert result.citations[0].chunk_id == chunk.chunk_id
    assert "non-generative" in result.answer


async def test_ask_api_schema_validation_and_provider_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def override_session() -> Generator[object, None, None]:
        yield object()

    def provider_error(
        _db: object, question: str, top_k: int, debug_retrieval: bool = False
    ) -> AskResponse:
        return AskResponse(
            question=question,
            answer="The configured provider could not produce an answer.",
            status="provider_error",
            provider="mock",
            citations=[],
            retrieval=RetrievalResponse(
                search_type="semantic",
                model_id="test-model",
                model_revision="test-revision",
                distance_metric="cosine",
                retrieved_count=0,
                selected_count=0,
            ),
        )

    monkeypatch.setattr(main_module, "run_grounded_rag", provider_error)
    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/ask", json={"question": "Question", "top_k": 5})
            empty = await client.post("/api/v1/ask", json={"question": ""})
            invalid_top_k = await client.post(
                "/api/v1/ask", json={"question": "Question", "top_k": 21}
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "provider_error"
    assert response.json()["provider"] == "mock"
    assert response.json()["selected_evidence"] == []
    assert response.json()["debug_retrieval"] is None
    assert empty.status_code == 422
    assert invalid_top_k.status_code == 422
