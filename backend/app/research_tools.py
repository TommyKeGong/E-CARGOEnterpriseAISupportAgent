"""Deterministic, read-only research tools built on the local academic corpus."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.embeddings.local import (
    COSINE_DISTANCE_METRIC,
    LOCAL_MODEL_ID,
    LOCAL_MODEL_REVISION,
    TextEncoder,
    semantic_search,
)
from app.models import AcademicDocument, ChunkEmbedding, DocumentChunk
from app.schemas import (
    ResearchChunkPage,
    ResearchChunkReference,
    ResearchDocument,
    ResearchDocumentPage,
    ResearchPageContext,
    ResearchSearchResponse,
    ResearchSearchResult,
)

MAX_SEARCH_TOP_K = 20
MAX_PAGE_SIZE = 100
MAX_DOCUMENT_FILTERS = 20
MAX_QUERY_LENGTH = 500


class ResearchToolNotFoundError(LookupError):
    """Raised when a requested persisted document is absent."""


class ResearchTools:
    """A small, route-independent, read-only interface for research operations.

    The tools accept only persisted document identifiers and validated scalar inputs.
    They cannot read filesystem paths, issue arbitrary SQL, or execute commands.
    """

    def __init__(self, session: Session, encoder: TextEncoder) -> None:
        self._session = session
        self._encoder = encoder

    def search_papers(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Sequence[str] | None = None,
    ) -> ResearchSearchResponse:
        """Cosine-rank persisted chunks, optionally within explicit document IDs."""
        query = self._validate_query(query)
        self._validate_top_k(top_k)
        filter_ids = self._validate_document_ids(document_ids)
        self._require_documents(filter_ids)
        results = semantic_search(
            self._session,
            query,
            self._encoder,
            top_k=top_k,
            document_ids=filter_ids,
        )
        return ResearchSearchResponse(
            query=query,
            model_id=LOCAL_MODEL_ID,
            model_revision=LOCAL_MODEL_REVISION,
            distance_metric=COSINE_DISTANCE_METRIC,
            results=[
                ResearchSearchResult(
                    document_id=result.document_id,
                    source_filename=result.source_filename,
                    chunk_id=result.chunk_id,
                    pdf_page_number=result.pdf_page_number,
                    chunk_text=result.chunk_text,
                    similarity_score=result.similarity_score,
                )
                for result in results
            ],
        )

    def list_papers(self, page: int = 1, page_size: int = 20) -> ResearchDocumentPage:
        """Return a stable, explicitly paginated view of persisted documents."""
        offset = self._page_offset(page, page_size)
        chunk_count = func.count(DocumentChunk.chunk_id).label("chunk_count")
        rows = self._session.execute(
            select(AcademicDocument, chunk_count)
            .outerjoin(DocumentChunk, DocumentChunk.document_id == AcademicDocument.document_id)
            .group_by(AcademicDocument.document_id)
            .order_by(AcademicDocument.created_at, AcademicDocument.document_id)
            .offset(offset)
            .limit(page_size)
        ).all()
        total = self._session.scalar(select(func.count()).select_from(AcademicDocument)) or 0
        return ResearchDocumentPage(
            items=[self._document_result(document, chunk_count=count) for document, count in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_document(self, document_id: str) -> ResearchDocument:
        """Return persisted document metadata and indexing completeness."""
        return self._document_result(self._require_document(document_id))

    def read_chunks(
        self, document_id: str, page: int = 1, page_size: int = 20
    ) -> ResearchChunkPage:
        """Return stable, bounded chunks for exactly one persisted document."""
        self._require_document(document_id)
        offset = self._page_offset(page, page_size)
        total = self._session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        ) or 0
        chunks = self._session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .offset(offset)
            .limit(page_size)
        ).all()
        return ResearchChunkPage(
            document_id=document_id,
            items=[self._chunk_reference(chunk) for chunk in chunks],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_page_context(self, document_id: str, pdf_page_number: int) -> ResearchPageContext:
        """Return only persisted indexed chunks for one physical PDF page.

        It intentionally cannot reconstruct an original PDF page. A page with no
        extractable/indexed text is returned as an empty, explicitly incomplete context.
        """
        document = self._require_document(document_id)
        if pdf_page_number < 1 or pdf_page_number > document.page_count:
            raise ValueError("pdf_page_number must be within the document page count")
        chunks = self._session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .where(DocumentChunk.pdf_page_number == pdf_page_number)
            .order_by(DocumentChunk.chunk_index)
        ).all()
        references = [self._chunk_reference(chunk) for chunk in chunks]
        return ResearchPageContext(
            document_id=document_id,
            pdf_page_number=pdf_page_number,
            chunks=references,
            available_indexed_text="\n\n".join(chunk.chunk_text for chunk in references),
            indexed_text_available=bool(references),
            is_complete_original_pdf_page=False,
            context_note=(
                "Only persisted indexed chunks are available; this is not the original complete "
                "PDF page."
            ),
        )

    def _document_result(
        self, document: AcademicDocument, *, chunk_count: int | None = None
    ) -> ResearchDocument:
        if chunk_count is None:
            chunk_count = self._session.scalar(
                select(func.count())
                .select_from(DocumentChunk)
                .where(DocumentChunk.document_id == document.document_id)
            ) or 0
        embedding_count = self._session.scalar(
            select(func.count())
            .select_from(ChunkEmbedding)
            .join(DocumentChunk, DocumentChunk.chunk_id == ChunkEmbedding.chunk_id)
            .where(DocumentChunk.document_id == document.document_id)
            .where(ChunkEmbedding.model_id == LOCAL_MODEL_ID)
            .where(ChunkEmbedding.model_revision == LOCAL_MODEL_REVISION)
        ) or 0
        return ResearchDocument(
            document_id=document.document_id,
            source_filename=document.source_filename,
            title=document.title,
            authors=document.authors,
            publication_year=document.publication_year,
            publication_venue=document.publication_venue,
            doi=document.doi,
            rights_status=document.rights_status,
            page_count=document.page_count,
            chunk_count=chunk_count,
            embedding_count=embedding_count,
            indexing_status="indexed" if embedding_count == chunk_count else "indexing_incomplete",
            created_at=document.created_at,
        )

    @staticmethod
    def _chunk_reference(chunk: DocumentChunk) -> ResearchChunkReference:
        return ResearchChunkReference(
            document_id=chunk.document_id,
            source_filename=chunk.document.source_filename,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_index,
            pdf_page_number=chunk.pdf_page_number,
            chunk_text=chunk.chunk_text,
        )

    def _require_document(self, document_id: str) -> AcademicDocument:
        if not document_id:
            raise ValueError("document_id must not be empty")
        document = self._session.get(AcademicDocument, document_id)
        if document is None:
            raise ResearchToolNotFoundError(f"Document '{document_id}' was not found.")
        return document

    def _require_documents(self, document_ids: tuple[str, ...] | None) -> None:
        if document_ids is None:
            return
        existing = set(
            self._session.scalars(
                select(AcademicDocument.document_id).where(
                    AcademicDocument.document_id.in_(document_ids)
                )
            ).all()
        )
        missing = next(
            (document_id for document_id in document_ids if document_id not in existing), None
        )
        if missing is not None:
            raise ResearchToolNotFoundError(f"Document '{missing}' was not found.")

    @staticmethod
    def _validate_query(query: str) -> str:
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        query = query.strip()
        if not query or len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"query must contain 1 to {MAX_QUERY_LENGTH} characters")
        return query

    @staticmethod
    def _validate_top_k(top_k: int) -> None:
        if not 1 <= top_k <= MAX_SEARCH_TOP_K:
            raise ValueError(f"top_k must be between 1 and {MAX_SEARCH_TOP_K}")

    @staticmethod
    def _validate_document_ids(document_ids: Sequence[str] | None) -> tuple[str, ...] | None:
        if document_ids is None:
            return None
        ids = tuple(document_ids)
        if not ids or len(ids) > MAX_DOCUMENT_FILTERS or len(set(ids)) != len(ids):
            raise ValueError("document_ids must contain 1 to 20 unique document IDs")
        if any(not isinstance(document_id, str) or not document_id for document_id in ids):
            raise ValueError("document_ids must contain non-empty strings")
        return ids

    @staticmethod
    def _page_offset(page: int, page_size: int) -> int:
        if page < 1:
            raise ValueError("page must be at least 1")
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")
        return (page - 1) * page_size
