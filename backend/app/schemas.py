"""Pydantic request/response contracts for local inspection and grounded RAG endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PaperListItem(BaseModel):
    document_id: str
    source_filename: str
    title: str | None
    authors: list[str] | None
    publication_year: int | None
    page_count: int
    chunk_count: int


class PaperListResponse(BaseModel):
    """A bounded list of imported papers and their persisted counts."""

    items: list[PaperListItem]
    total: int


class PaperDetailResponse(PaperListItem):
    publication_venue: str | None
    doi: str | None
    rights_status: str


class PaperChunkResponse(BaseModel):
    chunk_id: str
    chunk_index: int
    pdf_page_number: int
    chunk_text: str


class PaperChunkPageResponse(BaseModel):
    document_id: str
    items: list[PaperChunkResponse]
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    total: int


class DocumentListItem(BaseModel):
    document_id: str
    source_filename: str
    title: str | None
    authors: list[str] | None
    page_count: int
    chunk_count: int
    created_at: datetime | None


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    total: int


class DocumentDetailResponse(DocumentListItem):
    publication_year: int | None
    publication_venue: str | None
    doi: str | None
    rights_status: str
    indexing_status: Literal["indexed", "indexing_incomplete"]
    embedding_count: int = Field(ge=0)


class DocumentUploadResponse(DocumentDetailResponse):
    ingestion_status: Literal["imported", "duplicate_skipped"]


class DocumentDeleteResponse(BaseModel):
    document_id: str
    status: Literal["deleted"]


class DocumentChunkPageResponse(BaseModel):
    document_id: str
    items: list[PaperChunkResponse]
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    total: int


class ResearchChunkReference(BaseModel):
    """Persisted source text and identifiers usable in a citation-compatible workflow."""

    document_id: str
    source_filename: str
    chunk_id: str
    chunk_index: int = Field(ge=0)
    pdf_page_number: int = Field(ge=1)
    chunk_text: str


class ResearchChunkPage(BaseModel):
    document_id: str
    items: list[ResearchChunkReference]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class ResearchDocument(BaseModel):
    document_id: str
    source_filename: str
    title: str | None
    authors: list[str] | None
    publication_year: int | None
    publication_venue: str | None
    doi: str | None
    rights_status: str
    page_count: int = Field(ge=1)
    chunk_count: int = Field(ge=0)
    embedding_count: int = Field(ge=0)
    indexing_status: Literal["indexed", "indexing_incomplete"]
    created_at: datetime | None


class ResearchDocumentPage(BaseModel):
    items: list[ResearchDocument]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class ResearchSearchResult(BaseModel):
    document_id: str
    source_filename: str
    chunk_id: str
    pdf_page_number: int = Field(ge=1)
    chunk_text: str
    similarity_score: float


class ResearchSearchResponse(BaseModel):
    query: str
    model_id: str
    model_revision: str
    distance_metric: Literal["cosine"]
    results: list[ResearchSearchResult]


class ResearchPageContext(BaseModel):
    document_id: str
    pdf_page_number: int = Field(ge=1)
    chunks: list[ResearchChunkReference]
    available_indexed_text: str
    indexed_text_available: bool
    is_complete_original_pdf_page: Literal[False] = False
    context_note: str


class KeywordSearchResult(BaseModel):
    document_id: str
    source_filename: str
    pdf_page_number: int
    chunk_id: str
    excerpt: str


class KeywordSearchResponse(BaseModel):
    """Result of PostgreSQL ILIKE matching; this is not semantic retrieval."""

    search_type: str = "keyword"
    query: str
    items: list[KeywordSearchResult]
    total: int


class SemanticSearchResult(BaseModel):
    document_id: str
    source_filename: str
    chunk_id: str
    pdf_page_number: int
    similarity_score: float
    excerpt: str


class SemanticSearchResponse(BaseModel):
    """Cosine-distance pgvector results for one local model family, not answer confidence."""

    search_type: str = "semantic"
    model_id: str
    model_revision: str
    distance_metric: str = "cosine"
    query: str
    results: list[SemanticSearchResult]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    debug_retrieval: bool = False


class AnswerCitation(BaseModel):
    document_id: str
    chunk_id: str
    source_filename: str
    pdf_page_number: int


class EvidenceResponse(BaseModel):
    """Full persisted source chunk selected for local evidence review."""

    document_id: str
    chunk_id: str
    source_filename: str
    pdf_page_number: int
    text: str
    similarity_score: float | None
    selected: bool = True


class DebugRetrievalResult(EvidenceResponse):
    """One ranked retrieval candidate and its evidence-selection result."""

    rank: int = Field(ge=1)
    selection_reason: str


class RetrievalResponse(BaseModel):
    search_type: Literal["semantic"]
    model_id: str
    model_revision: str
    distance_metric: Literal["cosine"]
    retrieved_count: int
    selected_count: int


class AskResponse(BaseModel):
    question: str
    answer: str | None
    status: Literal["answered", "evidence_retrieved", "insufficient_evidence", "provider_error"]
    provider: str
    citations: list[AnswerCitation]
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    debug_retrieval: list[DebugRetrievalResult] | None = None
    retrieval: RetrievalResponse
    invalid_citation_count: int = Field(default=0, ge=0)


class AgentAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    max_tool_calls: int = Field(default=5, ge=1, le=5)
    debug_trace: bool = False


class AgentTraceResponse(BaseModel):
    step: int = Field(ge=1)
    event: Literal["tool_call", "final", "limit_reached", "invalid_action", "provider_error"]
    tool_name: str | None = None
    result_item_count: int | None = Field(default=None, ge=0)
    message: str | None = None


class AgentAskResponse(BaseModel):
    question: str
    answer: str | None
    status: Literal["answered", "evidence_retrieved", "insufficient_evidence", "provider_error"]
    provider: str
    citations: list[AnswerCitation]
    evidence: list[EvidenceResponse]
    tool_call_count: int = Field(ge=0, le=5)
    execution_time_ms: int = Field(ge=0)
    invalid_citation_count: int = Field(default=0, ge=0)
    debug_trace: list[AgentTraceResponse] | None = None
