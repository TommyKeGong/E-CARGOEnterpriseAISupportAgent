"""Local sentence-transformer embeddings and model-scoped semantic retrieval."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from time import monotonic
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import AcademicDocument, ChunkEmbedding, DocumentChunk

LOCAL_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LOCAL_EMBEDDING_DIMENSION = 384
COSINE_DISTANCE_METRIC = "cosine"


class TextEncoder(Protocol):
    def encode(self, sentences: Sequence[str], **kwargs: object) -> object: ...


@dataclass(frozen=True)
class EmbeddingRunResult:
    processed: int
    skipped: int
    failed: int
    duration_seconds: float


@dataclass(frozen=True)
class SemanticResult:
    document_id: str
    source_filename: str
    chunk_id: str
    pdf_page_number: int
    chunk_text: str
    similarity_score: float


def validate_embedding(
    values: Sequence[float], dimension: int = LOCAL_EMBEDDING_DIMENSION
) -> list[float]:
    """Reject wrong-dimensional, NaN, and infinite vectors before persistence or search."""
    vector = [float(value) for value in values]
    if len(vector) != dimension:
        raise ValueError(f"expected embedding dimension {dimension}, received {len(vector)}")
    if not all(math.isfinite(value) for value in vector):
        raise ValueError("embedding contains NaN or infinity")
    return vector


@lru_cache(maxsize=1)
def get_local_encoder() -> TextEncoder:
    """Load the approved local model lazily from the sentence-transformers cache/source."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(LOCAL_MODEL_ID)
    dimension = model.get_embedding_dimension()
    if dimension != LOCAL_EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"{LOCAL_MODEL_ID} returned dimension {dimension}, expected {LOCAL_EMBEDDING_DIMENSION}"
        )
    return model


def _vectors(encoder: TextEncoder, texts: Sequence[str]) -> list[list[float]]:
    encoded = encoder.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
    return [validate_embedding(vector) for vector in encoded]


def generate_local_embeddings(
    session: Session,
    encoder: TextEncoder,
    *,
    batch_size: int = 32,
    model_id: str = LOCAL_MODEL_ID,
    document_id: str | None = None,
) -> EmbeddingRunResult:
    """Generate missing model-scoped vectors in batches and retain failed chunks for retry."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    started_at, processed, skipped, failed = monotonic(), 0, 0, 0
    last_chunk_id: str | None = None
    while True:
        statement = select(DocumentChunk).order_by(DocumentChunk.chunk_id).limit(batch_size)
        if document_id is not None:
            statement = statement.where(DocumentChunk.document_id == document_id)
        if last_chunk_id is not None:
            statement = statement.where(DocumentChunk.chunk_id > last_chunk_id)
        batch = session.scalars(statement).all()
        if not batch:
            break
        last_chunk_id = batch[-1].chunk_id
        existing_ids = set(
            session.scalars(
                select(ChunkEmbedding.chunk_id).where(
                    ChunkEmbedding.model_id == model_id,
                    ChunkEmbedding.chunk_id.in_([chunk.chunk_id for chunk in batch]),
                )
            ).all()
        )
        pending = [chunk for chunk in batch if chunk.chunk_id not in existing_ids]
        skipped += len(batch) - len(pending)
        if not pending:
            continue
        try:
            vectors = _vectors(encoder, [chunk.chunk_text for chunk in pending])
        except (TypeError, ValueError, RuntimeError):
            failed += len(pending)
            continue
        for chunk, vector in zip(pending, vectors, strict=True):
            try:
                with session.begin_nested():
                    session.add(
                        ChunkEmbedding(
                            chunk_id=chunk.chunk_id,
                            model_id=model_id,
                            dimension=LOCAL_EMBEDDING_DIMENSION,
                            embedding=vector,
                        )
                    )
                    session.flush()
                processed += 1
            except SQLAlchemyError:
                failed += 1
    return EmbeddingRunResult(processed, skipped, failed, monotonic() - started_at)


def semantic_search(
    session: Session,
    query: str,
    encoder: TextEncoder,
    *,
    top_k: int = 5,
    document_id: str | None = None,
    model_id: str = LOCAL_MODEL_ID,
) -> list[SemanticResult]:
    """Use pgvector cosine distance for one model family; never calculate similarity in Python."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    query_vector = _vectors(encoder, [query])[0]
    distance = ChunkEmbedding.embedding.cosine_distance(query_vector).label("cosine_distance")
    statement = (
        select(DocumentChunk, AcademicDocument.source_filename, distance)
        .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.chunk_id)
        .join(AcademicDocument, AcademicDocument.document_id == DocumentChunk.document_id)
        .where(ChunkEmbedding.model_id == model_id)
        .order_by(distance)
        .limit(top_k)
    )
    if document_id is not None:
        statement = statement.where(DocumentChunk.document_id == document_id)
    rows = session.execute(statement).all()
    return [
        SemanticResult(
            document_id=chunk.document_id,
            source_filename=source_filename,
            chunk_id=chunk.chunk_id,
            pdf_page_number=chunk.pdf_page_number,
            chunk_text=chunk.chunk_text,
            similarity_score=1.0 - float(cosine_distance),
        )
        for chunk, source_filename, cosine_distance in rows
    ]
