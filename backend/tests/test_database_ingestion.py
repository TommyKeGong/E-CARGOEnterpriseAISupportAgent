import os
from pathlib import Path

import pymupdf
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import create_database_engine
from app.ingestion.service import document_id_for, ingest_pdf
from app.models import AcademicDocument, DocumentChunk


def make_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "authorised fixture text " * 100)
    document.save(path)
    document.close()


@pytest.fixture()
def database_session() -> Session:
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


def test_metadata_identity_requires_sha256() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        document_id_for("not-a-sha")


def test_duplicate_ingestion_and_chunk_association(
    database_session: Session, tmp_path: Path
) -> None:
    path = tmp_path / "fixture.pdf"
    make_pdf(path)

    first = ingest_pdf(database_session, path)
    second = ingest_pdf(database_session, path)

    assert first.status == "imported"
    assert second.status == "duplicate_skipped"
    assert (
        database_session.scalar(
            select(AcademicDocument).where(AcademicDocument.document_id == first.document_id)
        )
        is not None
    )


def test_chunk_foreign_key_is_enforced(database_session: Session) -> None:
    database_session.add(
        DocumentChunk(
            chunk_id="invalid-foreign-key",
            document_id="missing-document",
            chunk_index=0,
            chunk_text="text",
            pdf_page_index=0,
            pdf_page_number=1,
        )
    )

    with pytest.raises(IntegrityError):
        database_session.flush()


def test_nested_transaction_rollback_leaves_no_document(
    database_session: Session, tmp_path: Path
) -> None:
    path = tmp_path / "rollback.pdf"
    make_pdf(path)
    with pytest.raises(RuntimeError):
        with database_session.begin_nested():
            result = ingest_pdf(database_session, path)
            raise RuntimeError("force rollback")

    assert (
        database_session.scalar(
            select(AcademicDocument).where(AcademicDocument.document_id == result.document_id)
        )
        is None
    )
