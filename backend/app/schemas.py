"""Pydantic response contracts for local corpus inspection endpoints."""

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
    distance_metric: str = "cosine"
    query: str
    results: list[SemanticSearchResult]
