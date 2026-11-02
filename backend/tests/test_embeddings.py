import os
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.main as main_module
from app.db import get_db_session
from app.embeddings.local import (
    LOCAL_EMBEDDING_DIMENSION,
    LOCAL_MODEL_REVISION,
    generate_local_embeddings,
    semantic_search,
    validate_embedding,
)
from app.main import app
from app.models import AcademicDocument, ChunkEmbedding, DocumentChunk


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


class FakeEncoder:
    def encode(self, sentences: list[str], **kwargs: object) -> list[list[float]]:
        vectors: list[list[float]] = []
        for sentence in sentences:
            vector = [0.0] * LOCAL_EMBEDDING_DIMENSION
            vector[0 if "role" in sentence.casefold() else 1] = 1.0
            vectors.append(vector)
        return vectors


def _document_with_chunks(session: Session, document_id: str) -> None:
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
            page_count=1,
        )
    )
    session.add_all(
        [
            DocumentChunk(
                chunk_id=f"{document_id}-role",
                document_id=document_id,
                section_id=None,
                chunk_index=0,
                chunk_text="Role-based collaboration assigns roles to agents.",
                pdf_page_index=0,
                pdf_page_number=1,
                printed_page_label=None,
            ),
            DocumentChunk(
                chunk_id=f"{document_id}-other",
                document_id=document_id,
                section_id=None,
                chunk_index=1,
                chunk_text="A separate topic uses other terminology.",
                pdf_page_index=0,
                pdf_page_number=1,
                printed_page_label=None,
            ),
        ]
    )
    session.flush()


def test_embedding_validation_rejects_invalid_vectors() -> None:
    assert len(validate_embedding([1.0] * LOCAL_EMBEDDING_DIMENSION)) == 384
    with pytest.raises(ValueError, match="dimension"):
        validate_embedding([1.0])
    with pytest.raises(ValueError, match="NaN"):
        validate_embedding([float("nan")] * LOCAL_EMBEDDING_DIMENSION)


def test_batch_generation_is_idempotent(database_session: Session) -> None:
    document_id = "TEST-EMBED-BATCH"
    _document_with_chunks(database_session, document_id)
    first = generate_local_embeddings(
        database_session,
        FakeEncoder(),
        batch_size=1,
        model_id="test-batch",
        document_id=document_id,
    )
    second = generate_local_embeddings(
        database_session,
        FakeEncoder(),
        batch_size=1,
        model_id="test-batch",
        document_id=document_id,
    )

    assert first.processed == 2
    assert first.failed == 0
    assert second.processed == 0
    assert second.skipped == 2
    assert (
        database_session.query(ChunkEmbedding)
        .filter_by(
            model_id="test-batch",
            model_revision=LOCAL_MODEL_REVISION,
            dimension=LOCAL_EMBEDDING_DIMENSION,
        )
        .count()
        == 2
    )


def test_semantic_ranking_and_document_filter(database_session: Session) -> None:
    document_id = "TEST-EMBED-SEARCH"
    _document_with_chunks(database_session, document_id)
    generate_local_embeddings(
        database_session, FakeEncoder(), model_id="test-search", document_id=document_id
    )

    results = semantic_search(
        database_session,
        "How are roles assigned?",
        FakeEncoder(),
        top_k=2,
        document_id=document_id,
        model_id="test-search",
    )

    assert [result.chunk_id for result in results] == [
        f"{document_id}-role",
        f"{document_id}-other",
    ]
    assert results[0].similarity_score > results[1].similarity_score
    with pytest.raises(ValueError, match="top_k"):
        semantic_search(database_session, "roles", FakeEncoder(), top_k=21, model_id="test-search")


async def test_semantic_api_schema_and_validation(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    document_id = "TEST-EMBED-API"
    _document_with_chunks(database_session, document_id)
    generate_local_embeddings(
        database_session,
        FakeEncoder(),
        model_id=main_module.LOCAL_MODEL_ID,
        document_id=document_id,
    )
    monkeypatch.setattr(main_module, "get_local_encoder", lambda: FakeEncoder())

    def overridden_session() -> Generator[Session, None, None]:
        yield database_session

    app.dependency_overrides[get_db_session] = overridden_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/papers/semantic-search",
                params={"q": "roles", "document_id": document_id, "top_k": 2},
            )
            empty = await client.get("/api/v1/papers/semantic-search?q=")
            invalid_top_k = await client.get("/api/v1/papers/semantic-search?q=roles&top_k=21")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["search_type"] == "semantic"
    assert response.json()["model_id"] == main_module.LOCAL_MODEL_ID
    assert response.json()["results"][0]["document_id"] == document_id
    assert empty.status_code == 422
    assert invalid_top_k.status_code == 422


async def test_semantic_api_handles_missing_model_and_database_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_model() -> FakeEncoder:
        raise RuntimeError("model unavailable")

    def available_session() -> Generator[object, None, None]:
        yield object()

    monkeypatch.setattr(main_module, "get_local_encoder", missing_model)
    app.dependency_overrides[get_db_session] = available_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            missing_model_response = await client.get("/api/v1/papers/semantic-search?q=roles")
    finally:
        app.dependency_overrides.clear()

    class FailingSession:
        def get(self, *args: object, **kwargs: object) -> None:
            raise SQLAlchemyError("database unavailable")

    def failing_session() -> Generator[FailingSession, None, None]:
        yield FailingSession()

    app.dependency_overrides[get_db_session] = failing_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            database_failure_response = await client.get("/api/v1/papers/semantic-search?q=roles")
    finally:
        app.dependency_overrides.clear()

    assert missing_model_response.status_code == 503
    assert database_failure_response.status_code == 503
