"""Transactional API coverage for local document management."""

import os
from collections.abc import Generator
from hashlib import sha256

import pymupdf
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.main as main_module
from app.db import create_database_engine, get_db_session
from app.embeddings.local import EmbeddingRunResult
from app.main import app
from app.models import AcademicDocument, ChunkEmbedding, DocumentChunk


class FakeEncoder:
    def encode(self, sentences: list[str], **_kwargs: object) -> list[list[float]]:
        return [[0.01] * 384 for _ in sentences]


def _pdf_bytes(*pages: str) -> bytes:
    document = pymupdf.open()
    for page_text in pages:
        page = document.new_page()
        page.insert_text((72, 72), page_text)
    payload = document.tobytes()
    document.close()
    return payload


@pytest.fixture()
def document_session(monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    database_url = os.environ.get("DATABASE_URL")
    if database_url is None:
        pytest.skip("DATABASE_URL required for PostgreSQL integration tests")
    engine = create_database_engine(database_url)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_session() -> Generator[Session, None, None]:
        request_session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield request_session
        finally:
            request_session.close()

    monkeypatch.setattr(main_module, "get_local_encoder", lambda: FakeEncoder())
    app.dependency_overrides[get_db_session] = override_session
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()


async def _upload(client: AsyncClient, payload: bytes, filename: str = "authorised.pdf"):
    return await client.post(
        "/api/v1/documents",
        files={"file": (filename, payload, "application/pdf")},
    )


async def test_valid_upload_generates_embeddings_and_duplicate_is_idempotent(
    document_session: Session,
) -> None:
    payload = _pdf_bytes("authorised E-CARGO evidence " * 40)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await _upload(client, payload)
        second = await _upload(client, payload)

    assert first.status_code == 201
    assert first.json()["ingestion_status"] == "imported"
    assert first.json()["indexing_status"] == "indexed"
    assert first.json()["embedding_count"] == first.json()["chunk_count"]
    assert first.json()["source_filename"] == "authorised.pdf"
    assert second.status_code == 200
    assert second.json()["ingestion_status"] == "duplicate_skipped"
    assert (
        document_session.scalar(
            select(func.count())
            .select_from(AcademicDocument)
            .where(AcademicDocument.content_hash == sha256(payload).hexdigest())
        )
        == 1
    )


async def test_upload_rejects_invalid_empty_and_oversized_files(
    document_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        invalid_type = await client.post(
            "/api/v1/documents",
            files={"file": ("invalid.txt", b"not a PDF", "text/plain")},
        )
        empty = await client.post(
            "/api/v1/documents",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        malformed = await client.post(
            "/api/v1/documents",
            files={"file": ("malformed.pdf", b"%PDF-not-a-document", "application/pdf")},
        )
        monkeypatch.setenv("DOCUMENT_UPLOAD_MAX_BYTES", "10")
        oversized = await _upload(client, _pdf_bytes("too large"))

    assert invalid_type.status_code == 415
    assert empty.status_code == 422
    assert malformed.status_code == 422
    assert oversized.status_code == 413
    assert document_session.scalar(select(func.count()).select_from(AcademicDocument)) == 2


async def test_document_listing_detail_chunks_and_transactional_deletion(
    document_session: Session,
) -> None:
    payload = _pdf_bytes("first page evidence " * 40, "second page evidence " * 40)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        upload = await _upload(client, payload, "inspect.pdf")
        document_id = upload.json()["document_id"]
        listing = await client.get("/api/v1/documents", params={"limit": 1, "offset": 0})
        detail = await client.get(f"/api/v1/documents/{document_id}")
        chunks = await client.get(
            f"/api/v1/documents/{document_id}/chunks",
            params={"limit": 10, "pdf_page_number": 2},
        )
        deletion = await client.delete(f"/api/v1/documents/{document_id}")
        missing = await client.get(f"/api/v1/documents/{document_id}")

    assert upload.status_code == 201
    assert listing.status_code == 200
    assert listing.json()["limit"] == 1
    assert detail.json()["indexing_status"] == "indexed"
    assert chunks.status_code == 200
    assert chunks.json()["total"] >= 1
    assert {item["pdf_page_number"] for item in chunks.json()["items"]} == {2}
    assert deletion.status_code == 200
    assert deletion.json() == {"document_id": document_id, "status": "deleted"}
    assert missing.status_code == 404
    assert (
        document_session.scalar(
            select(func.count())
            .select_from(ChunkEmbedding)
            .join(DocumentChunk, DocumentChunk.chunk_id == ChunkEmbedding.chunk_id)
            .where(DocumentChunk.document_id == document_id)
        )
        == 0
    )


async def test_delete_missing_document_returns_404(document_session: Session) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/api/v1/documents/does-not-exist")

    assert response.status_code == 404


async def test_embedding_failure_rolls_back_document_ingestion(
    document_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _pdf_bytes("rollback evidence " * 40)

    def failed_embeddings(*_args: object, **_kwargs: object) -> EmbeddingRunResult:
        return EmbeddingRunResult(processed=0, skipped=0, failed=1, duration_seconds=0.0)

    monkeypatch.setattr(main_module, "generate_local_embeddings", failed_embeddings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await _upload(client, payload, "rollback.pdf")

    assert response.status_code == 503
    assert (
        document_session.scalar(
            select(AcademicDocument).where(
                AcademicDocument.content_hash == sha256(payload).hexdigest()
            )
        )
        is None
    )
