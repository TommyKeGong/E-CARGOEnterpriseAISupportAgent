"""Offline tests for grounded RAG orchestration and citation validation."""

import json
import os
from collections.abc import Generator
from urllib.error import URLError

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
    OllamaModelNotFoundError,
    OllamaProvider,
    OllamaUnavailableError,
    ProviderError,
    ProviderOutput,
    ProviderOutputError,
    ProviderTimeoutError,
    get_default_provider,
)
from app.schemas import AskResponse, DebugRetrievalResult, EvidenceResponse, RetrievalResponse


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


def _evidence() -> list[Evidence]:
    return [
        Evidence(
            document_id="DOC-TEST",
            source_filename="test.pdf",
            chunk_id="DOC-TEST-C0001",
            pdf_page_number=4,
            chunk_text="E-CARGO assigns agents to roles.",
            similarity_score=0.8,
        )
    ]


def _ollama_envelope(answer: str, citations: list[dict[str, object]]) -> bytes:
    return json.dumps({"response": json.dumps({"answer": answer, "citations": citations})}).encode()


def test_ollama_provider_generates_grounded_structured_output() -> None:
    observed: dict[str, object] = {}

    def requester(url: str, body: bytes, timeout_seconds: float) -> tuple[int, bytes]:
        observed.update(url=url, request=json.loads(body), timeout_seconds=timeout_seconds)
        return 200, _ollama_envelope(
            "The evidence describes role assignment.",
            [
                {
                    "document_id": "DOC-TEST",
                    "chunk_id": "DOC-TEST-C0001",
                    "pdf_page_number": 4,
                }
            ],
        )

    output = OllamaProvider(model="configured-by-test", requester=requester).generate(
        "What does it describe?", _evidence()
    )

    assert output.status == "answered"
    assert output.answer == "The evidence describes role assignment."
    assert output.citations == [CitationCandidate("DOC-TEST", "DOC-TEST-C0001", 4)]
    assert observed["url"] == "http://127.0.0.1:11434/api/generate"
    assert observed["request"]["model"] == "configured-by-test"  # type: ignore[index]
    assert "untrusted data" in observed["request"]["prompt"]  # type: ignore[index]


def test_ollama_provider_preserves_chinese_question_in_grounded_prompt() -> None:
    observed: dict[str, object] = {}

    def requester(_url: str, body: bytes, _timeout_seconds: float) -> tuple[int, bytes]:
        observed["prompt"] = json.loads(body)["prompt"]
        return 200, _ollama_envelope(
            "证据描述了代理与角色之间的分配。",
            [
                {
                    "document_id": "DOC-TEST",
                    "chunk_id": "DOC-TEST-C0001",
                    "pdf_page_number": 4,
                }
            ],
        )

    output = OllamaProvider(model="configured-by-test", requester=requester).generate(
        "E-CARGO 如何分配代理和角色？", _evidence()
    )

    assert output.status == "answered"
    assert "E-CARGO 如何分配代理和角色？" in observed["prompt"]  # type: ignore[operator]


def test_ollama_provider_rejects_empty_evidence_without_a_request() -> None:
    provider = OllamaProvider(model="configured-by-test")

    with pytest.raises(ProviderError, match="selected evidence"):
        provider.generate("Question", [])


def test_ollama_provider_classifies_timeout_and_unavailable_service() -> None:
    def timeout_requester(_url: str, _body: bytes, _timeout: float) -> tuple[int, bytes]:
        raise TimeoutError

    def unavailable_requester(_url: str, _body: bytes, _timeout: float) -> tuple[int, bytes]:
        raise URLError("connection refused")

    with pytest.raises(ProviderTimeoutError):
        OllamaProvider(model="configured-by-test", requester=timeout_requester).generate(
            "Question", _evidence()
        )
    with pytest.raises(OllamaUnavailableError):
        OllamaProvider(model="configured-by-test", requester=unavailable_requester).generate(
            "Question", _evidence()
        )


def test_ollama_provider_classifies_missing_model_and_invalid_output() -> None:
    def missing_model(_url: str, _body: bytes, _timeout: float) -> tuple[int, bytes]:
        return 404, b'{"error":"model not found"}'

    def malformed_output(_url: str, _body: bytes, _timeout: float) -> tuple[int, bytes]:
        return 200, b'{"response":"not JSON"}'

    with pytest.raises(OllamaModelNotFoundError):
        OllamaProvider(model="missing", requester=missing_model).generate("Question", _evidence())
    with pytest.raises(ProviderOutputError):
        OllamaProvider(model="configured-by-test", requester=malformed_output).generate(
            "Question", _evidence()
        )


def test_ollama_provider_marks_an_empty_answer_as_insufficient_evidence() -> None:
    def abstaining_requester(_url: str, _body: bytes, _timeout: float) -> tuple[int, bytes]:
        return 200, _ollama_envelope("", [])

    output = OllamaProvider(model="configured-by-test", requester=abstaining_requester).generate(
        "Question", _evidence()
    )

    assert output.status == "insufficient_evidence"
    assert output.citations == []


def test_ollama_provider_rejects_empty_answer_with_citations_and_invalid_citation_shape() -> None:
    def empty_answer(_url: str, _body: bytes, _timeout: float) -> tuple[int, bytes]:
        return 200, _ollama_envelope(
            "",
            [{"document_id": "DOC-TEST", "chunk_id": "DOC-TEST-C0001", "pdf_page_number": 4}],
        )

    def invalid_citation(_url: str, _body: bytes, _timeout: float) -> tuple[int, bytes]:
        return 200, _ollama_envelope(
            "Answer",
            [{"document_id": "DOC-TEST", "chunk_id": "DOC-TEST-C0001", "pdf_page_number": "4"}],
        )

    with pytest.raises(ProviderOutputError):
        OllamaProvider(model="configured-by-test", requester=empty_answer).generate(
            "Question", _evidence()
        )
    with pytest.raises(ProviderOutputError):
        OllamaProvider(model="configured-by-test", requester=invalid_citation).generate(
            "Question", _evidence()
        )


def test_provider_selection_defaults_to_mock_and_controls_invalid_ollama_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAG_PROVIDER", raising=False)
    assert isinstance(get_default_provider(), MockLLMProvider)

    monkeypatch.setenv("RAG_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    with pytest.raises(ProviderError, match="OLLAMA_MODEL"):
        get_default_provider().generate("Question", _evidence())


def test_ollama_provider_requires_exactly_trusted_non_loopback_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = "http://192.0.2.44:11434"
    with pytest.raises(ProviderError, match="OLLAMA_TRUSTED_BASE_URL"):
        OllamaProvider(model="configured-by-test", base_url=endpoint)

    monkeypatch.setenv("OLLAMA_TRUSTED_BASE_URL", endpoint)
    provider = OllamaProvider(model="configured-by-test", base_url=endpoint)

    assert provider.base_url == endpoint
    with pytest.raises(ProviderError, match="OLLAMA_TRUSTED_BASE_URL"):
        OllamaProvider(model="configured-by-test", base_url="http://192.0.2.45:11434")


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
            CitationCandidate("wrong-document", chunk.chunk_id, 1),
            CitationCandidate(chunk.document_id, chunk.chunk_id, 2),
        ],
    )

    assert [citation.chunk_id for citation in validation.citations] == [chunk.chunk_id]
    assert validation.invalid_count == 3


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
    assert result.answer is None
    assert result.citations[0].chunk_id == chunk.chunk_id
    assert result.selected_evidence[0].original_chunk_text == chunk.chunk_text
    assert result.citations[0].pdf_page_number == result.selected_evidence[0].pdf_page_number


def test_orchestrator_debug_preserves_rank_and_unselected_reason(database_session: Session) -> None:
    chunk = _add_chunk(database_session, "TEST-RAG-DEBUG")
    result = GroundedRAGOrchestrator(
        provider=MockLLMProvider(),
        selector=EvidenceSelector(max_evidence=1),
        retriever=lambda *_args, **_kwargs: [_result(chunk), _result(chunk)],
    ).answer(database_session, "What is E-CARGO?", object(), top_k=2, debug_retrieval=True)

    assert len(result.debug_retrieval) == 2
    assert result.debug_retrieval[0].selection_reason == "selected"
    assert result.debug_retrieval[1].selection_reason == "duplicate_chunk_text"


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
            evidence=[],
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
    assert response.json()["evidence"] == []
    assert response.json()["debug_retrieval"] is None
    assert empty.status_code == 422
    assert invalid_top_k.status_code == 422


async def test_ask_api_exposes_selected_evidence_and_debug_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def override_session() -> Generator[object, None, None]:
        yield object()

    def evidence_response(
        _db: object, question: str, top_k: int, debug_retrieval: bool = False
    ) -> AskResponse:
        calls.append(debug_retrieval)
        evidence = EvidenceResponse(
            document_id="DOC-TEST",
            chunk_id="DOC-TEST-C0001",
            source_filename="test.pdf",
            pdf_page_number=4,
            text="Persisted local chunk text.",
            similarity_score=0.72,
            selected=True,
        )
        return AskResponse(
            question=question,
            answer=None,
            status="evidence_retrieved",
            provider="mock",
            citations=[],
            evidence=[evidence],
            debug_retrieval=(
                [
                    DebugRetrievalResult(
                        **evidence.model_dump(),
                        rank=1,
                        selection_reason="selected",
                    )
                ]
                if debug_retrieval
                else None
            ),
            retrieval=RetrievalResponse(
                search_type="semantic",
                model_id="test-model",
                model_revision="test-revision",
                distance_metric="cosine",
                retrieved_count=top_k,
                selected_count=1,
            ),
        )

    monkeypatch.setattr(main_module, "run_grounded_rag", evidence_response)
    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            debug_response = await client.post(
                "/api/v1/ask",
                json={"question": "What is E-CARGO?", "top_k": 5, "debug_retrieval": True},
            )
            default_response = await client.post(
                "/api/v1/ask", json={"question": "What is E-CARGO?", "top_k": 5}
            )
    finally:
        app.dependency_overrides.clear()

    assert calls == [True, False]
    assert debug_response.json()["answer"] is None
    assert debug_response.json()["evidence"][0]["text"] == "Persisted local chunk text."
    assert debug_response.json()["debug_retrieval"][0]["rank"] == 1
    assert default_response.json()["debug_retrieval"] is None
