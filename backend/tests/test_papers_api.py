from collections.abc import Generator
from contextlib import contextmanager

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import create_database_engine, get_db_session, session_factory
from app.main import app
from app.models import AcademicDocument, DocumentChunk


@contextmanager
def _session() -> Generator[Session, None, None]:
    session = session_factory(create_database_engine())()
    try:
        yield session
    finally:
        session.close()


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_paper_list_and_detail_use_imported_data() -> None:
    async with await _client() as client:
        response = await client.get("/api/v1/papers")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert {item["chunk_count"] for item in body["items"]} == {21, 157}
        document_id = body["items"][0]["document_id"]

        detail = await client.get(f"/api/v1/papers/{document_id}")

    assert detail.status_code == 200
    assert detail.json()["document_id"] == document_id
    assert detail.json()["rights_status"] == "unknown"


async def test_chunk_pagination_and_unknown_document() -> None:
    async with await _client() as client:
        papers = (await client.get("/api/v1/papers")).json()["items"]
        document_id = papers[0]["document_id"]
        first_page = await client.get(f"/api/v1/papers/{document_id}/chunks?limit=1&offset=0")
        second_page = await client.get(f"/api/v1/papers/{document_id}/chunks?limit=1&offset=1")
        missing = await client.get("/api/v1/papers/does-not-exist")

    assert first_page.status_code == 200
    assert first_page.json()["total"] == papers[0]["chunk_count"]
    assert first_page.json()["items"][0]["chunk_index"] == 0
    assert second_page.json()["items"][0]["chunk_index"] == 1
    assert missing.status_code == 404


async def test_keyword_search_is_bounded_and_empty_query_is_rejected() -> None:
    async with await _client() as client:
        response = await client.get("/api/v1/papers/search", params={"q": "E-CARGO", "limit": 2})
        empty = await client.get("/api/v1/papers/search?q=")

    assert response.status_code == 200
    assert response.json()["search_type"] == "keyword"
    assert response.json()["total"] <= 2
    assert empty.status_code == 422


async def test_database_errors_are_controlled() -> None:
    class FailingSession:
        def execute(self, *args: object, **kwargs: object) -> None:
            raise SQLAlchemyError("test database failure")

    def failing_session() -> Generator[FailingSession, None, None]:
        yield FailingSession()

    app.dependency_overrides[get_db_session] = failing_session
    try:
        async with await _client() as client:
            response = await client.get("/api/v1/papers")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "database" in response.json()["detail"].lower()


async def test_read_only_endpoints_do_not_mutate_database() -> None:
    with _session() as session:
        before = (
            session.scalar(select(func.count()).select_from(AcademicDocument)),
            session.scalar(select(func.count()).select_from(DocumentChunk)),
        )

    async with await _client() as client:
        papers = (await client.get("/api/v1/papers")).json()["items"]
        document_id = papers[0]["document_id"]
        await client.get(f"/api/v1/papers/{document_id}")
        await client.get(f"/api/v1/papers/{document_id}/chunks?limit=2")
        await client.get("/api/v1/papers/search", params={"q": "E-CARGO"})

    with _session() as session:
        after = (
            session.scalar(select(func.count()).select_from(AcademicDocument)),
            session.scalar(select(func.count()).select_from(DocumentChunk)),
        )

    assert after == before
