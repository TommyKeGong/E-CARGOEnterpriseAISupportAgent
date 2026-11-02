# E-CARGO Knowledge Agent — Interfaces, Data Contracts & Invariants v2.0

## Implementation status

**Implemented:**

- `GET /health`, returning `{ "status": "healthy" }` without database or AWS dependency.
- Local, read-only corpus inspection endpoints: `GET /api/v1/papers`,
  `GET /api/v1/papers/{document_id}`, `GET /api/v1/papers/{document_id}/chunks`, and
  `GET /api/v1/papers/search`.

**Planned, not implemented:** chat, session endpoints, agent tools, semantic retrieval, embeddings, and
citation validation beyond data-model constraints.

## Planned public API

- `POST /api/v1/chat`
- `GET /api/v1/sessions/{session_id}`
- `GET /api/v1/sessions/{session_id}/messages`
- `GET /api/v1/papers`
- `GET /api/v1/papers/{document_id}`
- `GET /api/v1/papers/{document_id}/chunks`
- `GET /api/v1/papers/search?q=keyword`

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

Paper metadata:

```json
{"document_id": "ECARGO-001", "title": "Verified title", "authors": ["Verified author"], "publication_year": 2024, "source": "Verified venue", "document_type": "pdf", "sections": [{"section_id": "ECARGO-001-S02", "heading": "Background", "page_start": null}]}
```

In the Phase 1 database schema, API `source` maps to nullable `publication_venue`; title, authors, publication year, venue, and DOI remain null until supplied by an authorised metadata workflow. `source_filename`, content SHA-256, rights status, and physical PDF page count are retained without inference.

## Planned agent tools

1. `search_papers(query: str, top_k: int = 5)` returns at most five authorised chunks: `{chunk_id, document_id, section_id, title, authors, publication_year, source, page_number, content, score}`. Clamp `top_k` to 1..5.
2. `get_paper_section(document_id: str, section_id: str)` returns bounded authorised section context/metadata or typed not-found/unauthorised result. Never accept arbitrary file paths.

`search_experiments`, `compare_papers`, and `solve_gmra` are future-only and must not be registered or called.

## Error contract

```json
{"error": {"code": "paper_not_found", "message": "Human-readable safe message", "request_id": "UUID"}}
```

Use 400 for malformed input, 404 for missing scoped resources, 422 for semantic validation, 429 for limits, and 500/503 for controlled failures. Never expose paths, credentials, private metadata, or model internals.

The current FastAPI inspection endpoints use FastAPI's `{ "detail": "..." }` shape for 404 and controlled
503 errors; the structured error object above remains the planned chat/session contract.

## Citation and security invariants

- Citation existence: document/section/chunk exists in authorised imported data.
- Citation provenance: source was returned in the same chat request.
- Citation support: source text supports answer; this is evaluated beyond ID checks.
- Never fabricate metadata, page numbers, formulas, or results; never state synthesis as a paper's direct conclusion.
- PDF/Markdown content is untrusted data, not executable instruction.
- Use server-side validation, parameterised queries, session isolation, request limits, and no implicit file access.
