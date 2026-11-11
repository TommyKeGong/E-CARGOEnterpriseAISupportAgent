# E-CARGO Knowledge Agent — Architecture & Technology Specification v2.0

## Scope

E-CARGO Knowledge Agent is a local-first academic RAG assistant for authorised research on Role-Based Collaboration (RBC), E-CARGO, GRA, GMRA, role assignment, E-CARGO mathematics, and documented applications including immigration policy simulation, clinical therapy planning, and scheduling. MVP scope is literature-grounded question answering only.

GMRA solving, optimisation, arbitrary code execution, experiment execution, automatic mathematical-model generation, automatic document download, and publication of restricted material are explicitly out of scope. They need separate future design and safety review.

## Technology matrix

| Layer | Choice | Purpose |
|---|---|---|
| Runtime | Python 3.12 | Application language |
| HTTP | FastAPI + Uvicorn | REST endpoints and Swagger |
| Validation | Pydantic v2 | Request/response schemas |
| Agent | Strands Agents SDK | One request-scoped research agent |
| LLM | Amazon Bedrock; Nova Lite candidate | Evidence-aware answer drafting |
| Embedding baseline | Sentence Transformers `paraphrase-multilingual-MiniLM-L12-v2` at `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, 384-d | Local Phase 2A literature/query vectors |
| Planned embedding | Titan Text Embeddings V2, 512-d | Future approved AWS comparison, kept separate from the local baseline |
| Persistence | PostgreSQL 16 + pgvector | Metadata, chunks, vectors, sessions |
| Data access | SQLAlchemy 2.x + Psycopg 3 | Transactions and parameterised queries |
| Migrations | Alembic | Versioned schema |
| Corpus files | Local authorised PDF/Markdown, read-only mount | Source preservation |
| Containers | Docker Compose | Local API + database |
| Testing | pytest + HTTPX | Unit, integration, API tests |
| Quality / CI | Ruff / GitHub Actions | Quality and repeatability |

## High-level flow

```text
Client / Swagger
  -> FastAPI (validation, session handling, limits)
  -> Grounded RAG orchestrator
       -> semantic retrieval -> pgvector -> model/revision-scoped paper chunks
       -> evidence selector -> bounded, exact-deduplicated evidence registry + selection audit
       -> provider interface -> Mock provider (default) | local Ollama provider (implemented, not live-verified) | approved Bedrock/Strands (future)
       -> citation validator -> structurally verified citations or abstention
  -> answer response + retrieval/citation audit metadata
```

## Academic corpus and ingestion

Ingest only material the user provides, is authorised to use, or is publicly usable. Do not put source documents in Git unless redistribution rights are confirmed.

1. Register `document_id`, title, authors, publication year, source/venue, document type, rights/provenance, and content hash.
2. Ingest PDF and Markdown while preserving originals in an authorised read-only mount.
3. Extract sections/text. Store page numbers only with a reliable original-PDF mapping; otherwise use section identity and null page metadata.
4. Chunk on headings and intact logical passages using deterministic IDs and content hashes.
5. Phase 2A generates normalised local 384-dimensional vectors using `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; rejects wrong dimensions, NaN, and infinity, and skips existing `(chunk_id, model_id)` records. It does not upload corpus text.
6. A future approved Titan run generates normalised 512-dimensional vectors in a separate model family. Never pad, overwrite, or cross-compare vectors from different model families.
7. Upsert papers, sections, chunks, and vectors transactionally; re-ingestion must be idempotent and handle stale chunks.
8. Phase 4A document uploads accept only bounded multipart PDFs. The upload is written to an OS-managed temporary
   file with no user-controlled path, parsed by the existing pipeline, embedded with the pinned local model, and
   removed in all outcomes. Metadata, chunks, and embeddings commit together; an incomplete embedding run rolls
   the document insertion back. Uploaded originals are not retained by this API.

## Retrieval and answer workflow

1. Receive question and session scope.
2. Phase 2A generates a 384-dimensional local query embedding matching its stored local-model **and
   revision** configuration.
3. PostgreSQL pgvector calculates cosine distance and returns top-k chunks with document, section, text, score, and reliable page metadata. Do not calculate corpus similarity in Python and do not compare model families.
4. Evidence selection bounds total characters, deduplicates exact chunk text, retains provenance, and may
   abstain when no result clears its retrieval-eligibility threshold. This threshold is not answer confidence.
5. The Phase 3A default provider is an explicitly labelled, non-generative local Mock provider. It produces no
   scholarly synthesis. The optional Phase 3B Ollama provider is enabled only with `RAG_PROVIDER=ollama` and a
   user-selected `OLLAMA_MODEL`. A loopback endpoint is allowed by default; a non-loopback endpoint must exactly
   match the explicit `OLLAMA_TRUSTED_BASE_URL` acknowledgement before selected evidence is transmitted. It
   requests JSON answer/citation output and is never allowed to choose citations outside that evidence set.
6. Validate provider citations against the request-scoped evidence registry and authoritative chunk/document/
   page fields in PostgreSQL. Reject citations outside the retrieved set or with mismatched IDs/pages.
7. Explicitly abstain when evidence is insufficient or structural citation validation fails.
   Provider unavailability, timeout, missing local model, or malformed model output is distinct from an
   evidence insufficiency abstention.
8. In local-development inspection mode only, return selected persisted chunk text and optional ranked
   retrieval/selection audit. Do not log it or expose it in a public deployment without rights-aware access
   control.

## Phase 4B deterministic research tools

`ResearchTools` is a route-independent, read-only Python layer over the existing SQLAlchemy models and local
retriever. It provides bounded `search_papers`, `list_papers`, `get_document`, `read_chunks`, and
`get_page_context` operations for a future supervised agent integration. Search delegates to the same pinned,
model/revision-scoped pgvector cosine retrieval; it may restrict results to an explicit bounded set of persisted
document IDs. All results preserve document, chunk, source filename, and physical-page provenance.

The tools do not expose filesystem paths, arbitrary SQL, shell execution, writes, or network capabilities.
`get_page_context` concatenates only persisted chunks mapped to a physical PDF page. It always labels the result
as incomplete relative to the original PDF page, including when no indexed text exists. The one HTTP adapter,
`GET /api/v1/documents/{document_id}/pages/{pdf_page_number}/context`, is read-only and exists only because the
existing document API had no page-context aggregation capability.

## Phase 4C bounded research-agent orchestration

`BoundedResearchAgent` is request-scoped and owns a fixed registry of the five Phase 4B tools. A configured
Ollama provider returns strict JSON for either one tool action or a final answer; the backend validates action
shape/arguments, runs the tool, bounds serialized tool output, accumulates citation-compatible chunk evidence,
and validates final citations against that request-scoped evidence and PostgreSQL. The Mock agent retrieves
evidence but returns no generated answer.

Server limits are environment-configurable but never exceed five calls, eight steps, fifteen evidence items,
20,000 tool-result characters, and 180 seconds. Tool text is marked untrusted in prompts and cannot change the
fixed registry or execution policy. No model output can cause filesystem, shell, SQL, network, or write access.
Structural citation validation establishes provenance only, not semantic entailment.

## Logical data model

- `papers(document_id PK, title NULL, authors JSONB NULL, publication_year NULL, publication_venue NULL, doi NULL, source_filename, rights_status, content_hash, page_count, created_at)`
- `paper_sections(section_id PK, document_id FK, heading, ordinal, page_start NULL, page_end NULL, content, content_hash)`
- `paper_chunks(chunk_id PK, document_id FK, section_id FK, chunk_ordinal, content, embedding vector(512) NULL, content_hash)`
- `chunk_embeddings(embedding_id PK, chunk_id FK, model_id, model_revision, dimension, embedding vector, created_at, UNIQUE(chunk_id, model_id, model_revision))`; legacy vectors whose actual revision was not recorded are explicitly `unknown`; the pinned local rows use `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. The local Phase 2A partial HNSW index casts only 384-dimensional local rows to `vector(384)` with cosine ops.
- `chat_sessions(session_id UUID PK, created_at, updated_at)`
- `chat_messages(message_id UUID PK, session_id FK, role, content, created_at)`
- `retrieval_events(event_id UUID PK, session_id FK, query, evidence_ids JSONB, created_at)`

Use Alembic, foreign keys, indexes, transactions, and parameterised queries. Add ownership/auth fields before multi-user public deployment.

## Local document management boundary

`POST /api/v1/documents` and `DELETE /api/v1/documents/{document_id}` are local/private research operations.
They have no authentication and must not be exposed publicly. The upload route accepts `application/pdf`, checks
its extension, bounded byte size, `%PDF-` signature, and PyMuPDF parseability before ingestion. It returns only
safe source filenames and metadata, never temporary paths. Deletion removes only the requested document's
model-scoped embeddings, chunks, sections, and document row in one transaction.

## Citation, safety, and operating boundaries

- A citation identifies an imported paper and section/chunk returned in the same request.
- Citation provenance is necessary but semantic support needs evaluation and human review.
- Phase 3A citation validation is structural: it establishes that a citation is in the retrieved evidence set
  and its document/chunk/page fields agree with PostgreSQL. It does not prove that the answer's wording is
  semantically entailed by that evidence.
- Page metadata is optional and never inferred from text position.
- Source text is untrusted input; it cannot invoke tools or override policy.
- Bound request length, tool calls, retrieval count, and model timeouts. Exclude secrets and unnecessary raw content from logs.
- Keep PostgreSQL on `127.0.0.1`; use ignored credentials. Bedrock calls require explicit approval and least privilege.

## Phase 5A local frontend boundary

The separate `frontend/` Vite application is a presentation client, not an agent or a second data path. It calls
only the documented FastAPI document, RAG, agent, and indexed-page-context endpoints through a configurable
`VITE_API_BASE_URL`. It must render returned provenance exactly as supplied by the backend and must not invent
papers, answer text, citations, scores, page content, or agent actions. The browser’s Sources view obtains only
persisted indexed context and always preserves the backend statement that it is not an original complete PDF
page.

For local development, FastAPI accepts only explicitly configured `FRONTEND_ORIGINS` (default Vite loopback
origins), no wildcard origin and no browser credentials. The unauthenticated upload and deletion endpoints remain
local/private-only; this frontend does not authorise public exposure or weaken the backend's tool, citation, or
execution boundaries.

## Feasibility gates

- Local foundation: Python, Docker, API health, PostgreSQL, and pgvector are verified in `PROJECT_STATE.md`.
- Local semantic-retrieval gate: the local model, 384-d dimension, database count, idempotent rerun, pgvector ranking, and API contract are verified in `PROJECT_STATE.md`. Retrieval relevance remains for human annotation.
- Phase 3A gate: offline mock-provider orchestration, evidence limits, structural citation rejection, and the
  `/api/v1/ask` contract are testable without cloud credentials. This is not evidence of real LLM answer quality.
- AWS gate: Titan V2 512-d output and chosen model require approved live verification.
- Strands gate: installed SDK must complete the two-tool workflow in an approved real invocation.
- Academic RAG gate: ingestion, retrieval, citation validation, and abstention must pass evaluation before completion claims.
