# E-CARGO Knowledge Agent — Interfaces, Data Contracts & Invariants v2.0

## Implementation status

**Implemented:**

- `GET /health`, returning `{ "status": "healthy" }` without database or AWS dependency.
- Local, read-only corpus inspection endpoints: `GET /api/v1/papers`,
  `GET /api/v1/papers/{document_id}`, `GET /api/v1/papers/{document_id}/chunks`, and
  `GET /api/v1/papers/search`.
- Local, read-only semantic retrieval: `GET /api/v1/papers/semantic-search`.
- `POST /api/v1/ask`, implemented with an explicitly labelled local Mock provider by default and an optional,
  environment-selected Ollama provider. The configured user-authorised private Ollama endpoint completed one
  live structural-citation integration check; this is not a semantic-grounding or answer-quality result.
- Local/private document management: `POST /api/v1/documents`, `GET /api/v1/documents`,
  `GET /api/v1/documents/{document_id}`, `GET /api/v1/documents/{document_id}/chunks`, and
  `DELETE /api/v1/documents/{document_id}`.
- Local read-only indexed page context: `GET /api/v1/documents/{document_id}/pages/{pdf_page_number}/context`.
- Bounded local research agent: `POST /api/v1/agent/ask`.

**Planned, not implemented:** chat/session persistence, Strands tools, a real LLM provider, semantic
evidence-support evaluation, and Amazon Titan retrieval. The implemented ask path is grounded orchestration
with a non-generative Mock provider, not evidence of Agentic RAG answer quality.

## Planned public API

- `POST /api/v1/chat`
- `GET /api/v1/sessions/{session_id}`
- `GET /api/v1/sessions/{session_id}/messages`
- `GET /api/v1/papers`
- `GET /api/v1/papers/{document_id}`
- `GET /api/v1/papers/{document_id}/chunks`
- `GET /api/v1/papers/search?q=keyword`
- `GET /api/v1/papers/semantic-search?q=natural-language-query`
- `POST /api/v1/ask`

### Chat

Request:

```json
{"session_id": "optional UUID", "message": "research question"}
```

`message` is required and bounded. When `session_id` is omitted, backend generates a UUID, persists it, and returns it. A supplied ID must be valid and authorised; never silently substitute a different session.

Response:

```json
{
  "session_id": "UUID",
  "answer": "Evidence-grounded answer or explicit insufficient-evidence statement.",
  "citations": [{"document_id": "ECARGO-001", "section_id": "ECARGO-001-S02", "chunk_id": "ECARGO-001-S02-C01", "title": "Imported title", "authors": ["Author"], "publication_year": 2024, "source": "Verified venue", "page_number": null}],
  "next_actions": ["Optional evidence-safe follow-up"],
  "evidence_sufficient": true
}
```

`page_number` is an integer only with reliable extraction; otherwise null. Insufficient-evidence answers set `evidence_sufficient` false, make no invented citation, and explain the limitation.

### Sessions and papers

### Documents

- `POST /api/v1/documents` accepts one `multipart/form-data` field named `file`. It only accepts a plain
  `.pdf` filename and `application/pdf` content type. The streamed file is limited by
  `DOCUMENT_UPLOAD_MAX_BYTES` (25 MiB by default), must begin `%PDF-`, and must pass existing PyMuPDF parsing.
  The temporary source is always removed after ingestion. A new document returns 201 with
  `ingestion_status: "imported"`; a same-SHA-256 duplicate returns 200 with
  `ingestion_status: "duplicate_skipped"`. The response includes metadata, `chunk_count`, pinned-model
  `embedding_count`, and `indexing_status`. A failed embedding run rolls back the document/chunks/vectors.
- `GET /api/v1/documents?limit=20&offset=0` is a paginated metadata list. It returns `{items, limit, offset,
  total}`; every item has document ID, source filename, nullable title/authors, page/chunk counts, and creation
  time. It never returns local source paths.
- `GET /api/v1/documents/{document_id}` returns metadata, safe filename, page/chunk/embedding counts, and
  `indexed` or `indexing_incomplete` status. Unknown IDs return 404.
- `GET /api/v1/documents/{document_id}/chunks?limit=20&offset=0&pdf_page_number=optional` returns paginated
  `{chunk_id, chunk_index, chunk_text, pdf_page_number}` data for one document. `pdf_page_number` filters only
  physical PDF pages and is not an inferred printed label.
- `DELETE /api/v1/documents/{document_id}` transactionally deletes only that document's `chunk_embeddings`,
  chunks, sections, and paper row. It returns `{document_id, status: "deleted"}` or 404. The endpoint is
  unauthenticated and local/private-only; a public deployment needs authentication and an authorisation policy.
- `GET /api/v1/documents/{document_id}/pages/{pdf_page_number}/context` returns the persisted chunks mapped to
  one physical PDF page and their concatenated `available_indexed_text`. It returns
  `is_complete_original_pdf_page: false` in every response: this is indexed extraction context, never a PDF-page
  reconstruction. A valid source page with no extracted/indexed chunks returns an empty context; an unknown
  document returns 404 and a page outside the document's physical page count returns 422.

- Session endpoints return scoped metadata and ordered messages.
- `GET /api/v1/papers` is implemented as an unpaginated, local inspection list. It returns
  `{items, total}`, where each item contains `document_id`, `source_filename`, nullable bibliographic
  fields, `page_count`, and persisted `chunk_count`. It must not expose restricted source files.
- `GET /api/v1/papers/{document_id}` is implemented and returns persisted detailed metadata plus
  `chunk_count`. It does not infer missing bibliographic values or return PDF files.
- `GET /api/v1/papers/{document_id}/chunks?limit=20&offset=0` is implemented for local inspection.
  `limit` is 1..100; `offset` is non-negative. It returns `{document_id, items, limit, offset, total}`;
  each item is `{chunk_id, chunk_index, pdf_page_number, chunk_text}`.
- `GET /api/v1/papers/search?q=keyword&limit=10` is implemented as bounded PostgreSQL `ILIKE`
  **Keyword Search**, not semantic search or RAG. `q` is 1..200 characters; `limit` is 1..20. It returns
  `{search_type: "keyword", query, items, total}` with bounded excerpts and physical PDF page numbers.
- All inspection endpoints are local-development-only and read-only. They have no authentication or
  authorisation layer and are not a public deployment interface.
- `GET /api/v1/papers/semantic-search?q=...&top_k=5&document_id=optional` is implemented as local
  **Semantic Search**. `q` is 1..500 characters; `top_k` is 1..20. It embeds the query with
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` and has PostgreSQL/pgvector cosine-rank
  rows from the same model ID. The response is `{search_type: "semantic", model_id, distance_metric:
  "cosine", query, results}`; each result includes document/source/chunk/page provenance, a bounded
  excerpt, and `similarity_score = 1 - cosine_distance`. The score is a ranking value, not an answer
  probability or a claim of evidence support. An unknown `document_id` returns 404; invalid query/top-k
  returns 422; unavailable local model/database returns controlled 503.
- `POST /api/v1/ask` accepts `{ "question": "...", "top_k": 5, "debug_retrieval": false }`, with a 1..500
  character question and 1..20 `top_k`. It returns `{question, answer, status, provider, citations, evidence,
  debug_retrieval, retrieval, invalid_citation_count}`. `status` is `answered`, `evidence_retrieved`,
  `insufficient_evidence`, or `provider_error`. `answered` is reserved for a real provider that generated an
  answer. The current `mock` provider returns `evidence_retrieved` and `answer: null`.
- Each selected `evidence` item is `{document_id, chunk_id, source_filename, pdf_page_number,
  similarity_score, selected: true, text}`. `text` is the full persisted source chunk in the local-development
  API; it is not provider-generated. The score is the retrieved cosine ranking score, not answer confidence
  or a proof of claim support. Citation IDs/pages must correspond to selected evidence and PostgreSQL.
- `debug_retrieval` defaults to `false`. When true, it returns all retrieved Top-K results with the same
  provenance/text/score plus `rank`, `selected`, and the actual `selection_reason` (`selected`,
  `below_minimum_similarity`, `duplicate_chunk_text`, `evidence_character_budget_exhausted`, or
  `max_evidence_reached`). Debug data is local-development-only and must not be logged or exposed publicly
  without authorisation and a rights-aware content policy. When false, no unselected candidates are returned.
- Retrieval includes `model_id`, `model_revision`, cosine metric, retrieved and selected counts. No selected
  evidence returns `insufficient_evidence`; a provider failure returns `provider_error`; citation validation
  failure rejects citations and returns `insufficient_evidence`.
- `RAG_PROVIDER` defaults to `mock`. `RAG_PROVIDER=ollama` requires `OLLAMA_MODEL`; `OLLAMA_BASE_URL` defaults
  to `http://127.0.0.1:11434`; `OLLAMA_TIMEOUT_SECONDS` defaults to 30. Loopback endpoints are allowed by
  default. A non-loopback endpoint is permitted only when it exactly equals `OLLAMA_TRUSTED_BASE_URL`, making
  the evidence-transmission choice explicit. The Ollama provider sends bounded selected evidence only, requests
  strict JSON `{answer, citations}`, and has no hard-coded model name or remote fallback. A model's empty
  answer plus empty citation list becomes
  `insufficient_evidence`; service, timeout, missing-model, or malformed-output failures become
  `provider_error`.

Paper metadata:

```json
{"document_id": "ECARGO-001", "title": "Verified title", "authors": ["Verified author"], "publication_year": 2024, "source": "Verified venue", "document_type": "pdf", "sections": [{"section_id": "ECARGO-001-S02", "heading": "Background", "page_start": null}]}
```

In the Phase 1 database schema, API `source` maps to nullable `publication_venue`; title, authors, publication year, venue, and DOI remain null until supplied by an authorised metadata workflow. `source_filename`, content SHA-256, rights status, and physical PDF page count are retained without inference.

## Planned agent tools

1. `search_papers(query: str, top_k: int = 5)` returns at most five authorised chunks: `{chunk_id, document_id, section_id, title, authors, publication_year, source, page_number, content, score}`. Clamp `top_k` to 1..5.
2. `get_paper_section(document_id: str, section_id: str)` returns bounded authorised section context/metadata or typed not-found/unauthorised result. Never accept arbitrary file paths.

`search_experiments`, `compare_papers`, and `solve_gmra` are future-only and must not be registered or called.

## Phase 4B research-tool interface

`app.research_tools.ResearchTools` is an implemented Python interface, not an autonomous agent registration.
It returns Pydantic-validated data and raises `ResearchToolNotFoundError` for unknown persisted documents:

1. `search_papers(query, top_k=5, document_ids=None)` validates a 1..500-character query, bounds `top_k` to
   1..20, validates up to 20 unique document IDs when supplied, and returns pgvector-ranked persisted chunk text
   with document/chunk/source/page provenance and a cosine ranking score.
2. `list_papers(page=1, page_size=20)` and `read_chunks(document_id, page=1, page_size=20)` use one-based,
   explicit pagination with `page_size` 1..100.
3. `get_document(document_id)` returns persisted metadata plus chunk/embedding indexing completeness.
4. `get_page_context(document_id, pdf_page_number)` returns only indexed chunks mapped to that physical page;
   it explicitly does not recreate the complete original PDF page.

The interface accepts no filesystem paths or executable input and has no write, arbitrary SQL, shell, or network
tool. Chunk provenance is structurally compatible with citation validation, but returned text is not itself proof
of semantic support for a future generated claim.

## Phase 4C bounded agent contract

`POST /api/v1/agent/ask` accepts `{question, max_tool_calls=5, debug_trace=false}`. The question is 1..500
characters and requested calls are 1..5. It returns `status`, nullable `answer`, structurally validated
citations, retrieved evidence, provider name, `tool_call_count`, `execution_time_ms`, invalid-citation count,
and an optional safe trace containing only event/tool/count/reason metadata. It never exposes prompts,
credentials, endpoints, or raw provider transport data.

Only `search_papers`, `list_papers`, `get_document`, `read_chunks`, and `get_page_context` can be called. Their
Pydantic argument contracts forbid unknown fields. Environment variables `AGENT_MAX_TOOL_CALLS`,
`AGENT_MAX_STEPS`, `AGENT_MAX_EVIDENCE_ITEMS`, `AGENT_MAX_TOOL_RESULT_CHARACTERS`, and
`AGENT_TIMEOUT_SECONDS` may tighten defaults but cannot exceed 5, 8, 15, 20,000, and 180 respectively. Invalid
actions/provider failures return `provider_error`; limits, empty evidence, or bad citations return a safe
`insufficient_evidence` response. `/api/v1/ask` is unchanged.

## Error contract

```json
{"error": {"code": "paper_not_found", "message": "Human-readable safe message", "request_id": "UUID"}}
```

Use 400 for malformed input, 404 for missing scoped resources, 422 for semantic validation, 429 for limits, and 500/503 for controlled failures. Never expose paths, credentials, private metadata, or model internals.

The current FastAPI inspection endpoints use FastAPI's `{ "detail": "..." }` shape for 404 and controlled
503 errors; the structured error object above remains the planned chat/session contract.

## Phase 5A browser-client contract

The local frontend uses `VITE_API_BASE_URL` and matches the existing Pydantic response shapes for
`POST /api/v1/ask`, `POST /api/v1/agent/ask`, document list/detail/upload/delete/chunk endpoints, and
`GET /api/v1/documents/{document_id}/pages/{pdf_page_number}/context`. It sends the existing request bodies
unchanged: RAG `{question, top_k, debug_retrieval}` and Agent `{question, max_tool_calls, debug_trace}`. It
does not call a non-existent PDF download, source-file, session, tool-execution, or arbitrary-search endpoint.

The browser presents backend `status`, nullable `answer`, citations, evidence, scores, and safe agent trace as
returned. It must label page context as indexed extraction rather than complete original PDF content. CORS is
restricted to the explicit `FRONTEND_ORIGINS` list, defaulting to Vite's loopback origins; no wildcard origin or
credentialed browser request is part of this contract.

## Citation and security invariants

- Citation existence: document/section/chunk exists in authorised imported data.
- Citation provenance: source was returned in the same chat request.
- Citation support: source text supports answer; this is evaluated beyond ID checks.
- Structural validation in Phase 3A checks that provider-supplied `document_id`, `chunk_id`, and physical PDF
  page match both a chunk from the request's selected evidence and the database. It rejects hallucinated,
  stale, mismatched, and un-retrieved citations. It does not establish semantic support.
- Never fabricate metadata, page numbers, formulas, or results; never state synthesis as a paper's direct conclusion.
- PDF/Markdown content is untrusted data, not executable instruction.
- Use server-side validation, parameterised queries, session isolation, request limits, and no implicit file access.
