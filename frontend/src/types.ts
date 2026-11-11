export type AnswerStatus =
  | 'answered'
  | 'evidence_retrieved'
  | 'insufficient_evidence'
  | 'provider_error'

export interface Citation {
  document_id: string
  chunk_id: string
  source_filename: string
  pdf_page_number: number
}

export interface Evidence {
  document_id: string
  chunk_id: string
  source_filename: string
  pdf_page_number: number
  text: string
  similarity_score: number | null
  selected: boolean
}

export interface Retrieval {
  search_type: 'semantic'
  model_id: string
  model_revision: string
  distance_metric: 'cosine'
  retrieved_count: number
  selected_count: number
}

export interface AskResponse {
  question: string
  answer: string | null
  status: AnswerStatus
  provider: string
  citations: Citation[]
  evidence: Evidence[]
  debug_retrieval: (Evidence & { rank: number; selection_reason: string })[] | null
  retrieval: Retrieval
  invalid_citation_count: number
}

export interface AgentTraceEntry {
  step: number
  event: 'tool_call' | 'final' | 'limit_reached' | 'invalid_action' | 'provider_error'
  tool_name: string | null
  result_item_count: number | null
  message: string | null
}

export interface AgentAskResponse {
  question: string
  answer: string | null
  status: AnswerStatus
  provider: string
  citations: Citation[]
  evidence: Evidence[]
  tool_call_count: number
  execution_time_ms: number
  invalid_citation_count: number
  debug_trace: AgentTraceEntry[] | null
}

export interface DocumentListItem {
  document_id: string
  source_filename: string
  title: string | null
  authors: string[] | null
  page_count: number
  chunk_count: number
  created_at: string | null
}

export interface DocumentListResponse {
  items: DocumentListItem[]
  limit: number
  offset: number
  total: number
}

export interface DocumentDetail extends DocumentListItem {
  publication_year: number | null
  publication_venue: string | null
  doi: string | null
  rights_status: string
  indexing_status: 'indexed' | 'indexing_incomplete'
  embedding_count: number
}

export interface DocumentChunk {
  chunk_id: string
  chunk_index: number
  pdf_page_number: number
  chunk_text: string
}

export interface DocumentChunkPage {
  document_id: string
  items: DocumentChunk[]
  limit: number
  offset: number
  total: number
}

export interface PageContext {
  document_id: string
  pdf_page_number: number
  chunks: Array<DocumentChunk & { document_id: string; source_filename: string }>
  available_indexed_text: string
  indexed_text_available: boolean
  is_complete_original_pdf_page: false
  context_note: string
}
