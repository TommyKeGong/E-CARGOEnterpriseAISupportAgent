"""Pydantic request/response contracts for local inspection and grounded RAG endpoints."""

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


class SelectedEvidence(BaseModel):
    """Full persisted source chunk selected for local evidence review."""

    document_id: str
    chunk_id: str
    source_filename: str
    pdf_page_number: int
    chunk_text: str
    similarity_score: float


class DebugRetrievalResult(SelectedEvidence):
    """One top-five retrieval candidate and its evidence-selection result."""

    selected: bool
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
    answer: str
    status: Literal["answered", "evidence_retrieved", "insufficient_evidence", "provider_error"]
    provider: str
    citations: list[AnswerCitation]
    selected_evidence: list[SelectedEvidence] = Field(default_factory=list)
    debug_retrieval: list[DebugRetrievalResult] | None = None
    retrieval: RetrievalResponse
    invalid_citation_count: int = Field(default=0, ge=0)
