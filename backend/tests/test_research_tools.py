"""Tests for deterministic, route-independent research tools."""

import os
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

import app.main as main_module
from app.db import create_database_engine, get_db_session
from app.embeddings.local import LOCAL_EMBEDDING_DIMENSION, generate_local_embeddings
from app.main import app
from app.models import AcademicDocument, DocumentChunk
from app.research_tools import ResearchToolNotFoundError, ResearchTools


class FakeEncoder:
    def encode(self, sentences: list[str], **_kwargs: object) -> list[list[float]]:
        vectors: list[list[float]] = []
        for sentence in sentences:
            vector = [0.0] * LOCAL_EMBEDDING_DIMENSION
            vector[0 if "role" in sentence.casefold() else 1] = 1.0
            vectors.append(vector)
        return vectors


@pytest.fixture()
def database_session() -> Generator[Session, None, None]:
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


def _add_document(
    session: Session,
    document_id: str,
    *,
    text_page_two: bool = True,
    with_embeddings: bool = True,
) -> None:
    session.add(
        AcademicDocument(
            document_id=document_id,
            title=None,
            authors=None,
            publication_year=None,
            publication_venue=None,
            doi=None,
            source_filename=f"{document_id}.pdf",
            content_hash=(document_id.lower() * 64)[:64],
            rights_status="unknown",
            page_count=2,
        )
    )
    chunks = [
        DocumentChunk(
            chunk_id=f"{document_id}-C0000",
            document_id=document_id,
            section_id=None,
            chunk_index=0,
            chunk_text="Role-based collaboration assigns agents to roles.",
            pdf_page_index=0,
            pdf_page_number=1,
            printed_page_label=None,
        )
    ]
    if text_page_two:
        chunks.append(
            DocumentChunk(
                chunk_id=f"{document_id}-C0001",
                document_id=document_id,
                section_id=None,
                chunk_index=1,
                chunk_text="Second indexed page context.",
                pdf_page_index=1,
                pdf_page_number=2,
                printed_page_label=None,
            )
        )
    session.add_all(chunks)
    session.flush()
    if with_embeddings:
        generate_local_embeddings(session, FakeEncoder(), document_id=document_id)


def test_search_results_keep_citation_compatible_metadata_and_filter_documents(
    database_session: Session,
) -> None:
    _add_document(database_session, "TEST-TOOLS-A")
    _add_document(database_session, "TEST-TOOLS-B")
    _add_document(database_session, "TEST-TOOLS-EMPTY", with_embeddings=False)
    tools = ResearchTools(database_session, FakeEncoder())

    filtered = tools.search_papers(
        "How are roles assigned?", top_k=5, document_ids=["TEST-TOOLS-A"]
    )
    empty = tools.search_papers("unrelated query", top_k=5, document_ids=["TEST-TOOLS-EMPTY"])

    assert filtered.model_id == main_module.LOCAL_MODEL_ID
    assert filtered.results
    assert {result.document_id for result in filtered.results} == {"TEST-TOOLS-A"}
    result = filtered.results[0]
    assert result.chunk_id.startswith("TEST-TOOLS-A-")
    assert result.pdf_page_number >= 1
    assert result.source_filename == "TEST-TOOLS-A.pdf"
    assert isinstance(result.chunk_text, str) and result.chunk_text
    assert isinstance(result.similarity_score, float)
    assert empty.results == []


def test_document_tools_paginate_and_handle_missing_resources(database_session: Session) -> None:
    _add_document(database_session, "TEST-TOOLS-LIST-A")
    _add_document(database_session, "TEST-TOOLS-LIST-B")
    tools = ResearchTools(database_session, FakeEncoder())

    papers = tools.list_papers(page=1, page_size=1)
    chunks = tools.read_chunks("TEST-TOOLS-LIST-A", page=2, page_size=1)
    detail = tools.get_document("TEST-TOOLS-LIST-A")

    assert papers.page == 1
    assert len(papers.items) == 1
    assert chunks.total == 2
    assert len(chunks.items) == 1
    assert chunks.items[0].chunk_index == 1
    assert detail.indexing_status == "indexed"
    with pytest.raises(ResearchToolNotFoundError):
        tools.get_document("does-not-exist")
    with pytest.raises(ResearchToolNotFoundError):
        tools.search_papers("roles", document_ids=["does-not-exist"])
    with pytest.raises(ValueError, match="page"):
        tools.list_papers(page=0)


def test_page_context_is_explicitly_limited_to_persisted_chunks(database_session: Session) -> None:
    _add_document(database_session, "TEST-TOOLS-PAGE", text_page_two=False)
    tools = ResearchTools(database_session, FakeEncoder())

    indexed = tools.get_page_context("TEST-TOOLS-PAGE", 1)
    missing = tools.get_page_context("TEST-TOOLS-PAGE", 2)

    assert indexed.indexed_text_available is True
    assert indexed.chunks[0].chunk_id == "TEST-TOOLS-PAGE-C0000"
    assert indexed.is_complete_original_pdf_page is False
    assert "not the original complete PDF page" in indexed.context_note
    assert missing.indexed_text_available is False
    assert missing.chunks == []
    assert missing.available_indexed_text == ""
    with pytest.raises(ValueError, match="page count"):
        tools.get_page_context("TEST-TOOLS-PAGE", 3)


async def test_page_context_api_uses_the_read_only_tool(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_document(database_session, "TEST-TOOLS-API", text_page_two=False)
    monkeypatch.setattr(main_module, "get_local_encoder", lambda: FakeEncoder())

    def override_session() -> Generator[Session, None, None]:
        yield database_session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/documents/TEST-TOOLS-API/pages/2/context")
            missing = await client.get("/api/v1/documents/does-not-exist/pages/1/context")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["indexed_text_available"] is False
    assert response.json()["is_complete_original_pdf_page"] is False
    assert missing.status_code == 404
