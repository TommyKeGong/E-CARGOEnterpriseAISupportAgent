# Architecture Decision Log

## ADR-015 — 2026-11-10 — Local frontend foundation with explicit development CORS
Status: Accepted (explicit user direction)

Decision: Add a separate React, TypeScript, Vite, and Tailwind browser client for the existing local FastAPI
contracts. Keep it presentation-only: no fabricated research data, no direct database/model access, and no
new backend capability. Permit only an explicit comma-separated local `FRONTEND_ORIGINS` CORS allowlist, with
Vite loopback origins as the default; do not use wildcard origins or browser credentials.

Consequences: The frontend can call the existing RAG, bounded Agent, document-management, and indexed
page-context APIs in local development. It does not make unauthenticated upload/delete endpoints safe for
public exposure, and it must preserve the backend's caveat that structural citation validity is not semantic
entailment and page context is not an original PDF-page reconstruction.

## ADR-014 — 2026-11-06 — Bounded local research-agent orchestration
Status: Accepted (explicit user direction)

Decision: Add a request-scoped `BoundedResearchAgent` over the fixed Phase 4B `ResearchTools` registry. An
Ollama model selects one strictly validated JSON action per step or returns a final JSON answer/citation set;
the backend owns execution, limits, evidence collection, and citation validation. The offline Mock provider
retrieves evidence but intentionally returns no scholarly synthesis.

Consequences: The agent cannot execute model-generated code, SQL, shell, network, filesystem, or unregistered
tools. Defaults/hard ceilings are five tool calls, eight steps, fifteen evidence items, 20,000 tool-result
characters, and 180 seconds. Retrieved text is untrusted data. Citation validation is request-scoped and
structural only; semantic support still requires evaluation and human review.

## ADR-013 — 2026-11-06 — Deterministic read-only research-tool foundation
Status: Accepted (explicit user direction)

Decision: Add a small, route-independent `ResearchTools` Python interface backed by the existing SQLAlchemy
models and pinned local pgvector retrieval. Its operations are bounded paper search, paper listing/detail,
chunk paging, and physical-page indexed context. Reuse existing document endpoints rather than duplicate them;
only expose a read-only page-context HTTP adapter. Page context consists solely of persisted mapped chunks and
always states that it is not a reconstructed original PDF page.

Consequences: No autonomous orchestration, LLM tool calling, schema change, filesystem access, arbitrary SQL,
shell execution, network capability, corpus re-ingestion, or write operation is introduced. Tool source
identifiers are citation-compatible provenance, but structural provenance remains insufficient to prove a future
answer is semantically supported.

## ADR-012 — 2026-11-06 — Local transactional document-management API
Status: Accepted (explicit user direction)

Decision: Add local/private multipart PDF upload, indexed document inspection, chunk inspection, and document
deletion routes. Reuse existing SHA-256 ingestion and the pinned local embedding pipeline; stage uploads only in
an OS temporary file, then remove it. Reject an incomplete embedding run and roll back the entire insertion.
Reuse the existing schema; manually delete dependent embeddings, chunks, and sections before the paper row in
one transaction.

Consequences: The API stores corpus text/chunks/vectors but does not retain upload originals. Upload and delete
routes remain unauthenticated and must never be publicly exposed without ownership, rights, and authorisation
controls. A duplicate SHA-256 is idempotent and does not regenerate embeddings.

## ADR-011 — 2026-11-05 — Optional local Ollama grounded-generation provider
Status: Accepted (explicit user direction)

Decision: Retain the offline `mock` provider as the default and add an optional `ollama` provider selected by
`RAG_PROVIDER`. The selected model name, URL, and timeout come only from environment variables; no model name
or endpoint is embedded in the business logic. Loopback URLs are allowed by default. A non-loopback endpoint
must exactly match `OLLAMA_TRUSTED_BASE_URL`, explicitly acknowledging that selected evidence is transmitted to
that host. The provider requests strict JSON answer/citation output and passes every claimed citation through
the existing request-scoped/database structural validator. No schema change, cloud client, model download, or
remote fallback is introduced.

Consequences: A model's empty answer with no citations is an insufficient-evidence abstention. Timeout,
unavailable service, missing model, and malformed output are provider errors. Structural citation validation
prevents unselected or mismatched source identifiers but does not establish semantic entailment or eliminate
hallucination; evaluation and human review remain necessary.

## ADR-010 — 2026-11-05 — Local evidence transparency and Mock status semantics
Status: Accepted

Decision: `POST /api/v1/ask` returns `evidence_retrieved` and `answer: null` for the non-generative Mock
provider. It returns full persisted selected chunk text, source/page provenance, and pgvector similarity score
for local inspection. An explicit `debug_retrieval` flag returns ranked Top-K candidates and factual selection
reasons. Scores remain ranking signals, not answer confidence or semantic-support proof.

Consequences: Local reviewers can inspect the exact material presented to a future real provider and spot
threshold/budget exclusions. Full text and debug data must not be logged or exposed in a production deployment
without authorisation, rights review, and access controls. Exact duplicate removal remains implemented; a
near-duplicate heuristic is deferred until evaluation can show it will not suppress useful evidence.

## ADR-001 — 2026-11-02 — Local-first MVP
Status: Accepted (from user discussion)
Decision: Develop on own computer with Docker Compose; postpone lab/VPS/AWS hosting. Use Bedrock as remote model service if access is verified.
Reason: Reduce infrastructure complexity and cost while developing core Agent/RAG backend.

## ADR-002 — 2026-11-02 — Single agent and four tools
Status: Superseded by ADR-005
Decision: Strands single agent with `search_kb`, `get_kb_doc`, `search_tickets`, `create_ticket_draft`; no multi-agent or external ticket submission.

## ADR-003 — 2026-11-02 — Data and retrieval
Status: Superseded by ADR-005
Decision: 15 synthetic Markdown KB docs; 60 historical tickets; Titan V2 512-d embeddings for KB; PostgreSQL pgvector cosine search; historical ticket search starts with SQL keyword/full-text search.
Note: Ticket search implementation is a design choice; adjust only after evaluation.

## ADR-004 — 2026-11-02 — Citation and write safety
Status: Partially superseded by ADR-005 (citation provenance and untrusted-retrieval rules remain applicable; ticket-draft rules do not)
Decision: Validate citation provenance in server code; require explicit intent for ticket draft writes; retrieved text is untrusted.

## ADR-005 — 2026-11-02 — E-CARGO Knowledge Agent scope migration
Status: Accepted (explicit user direction)
Decision: Supersede the Enterprise IT Helpdesk MVP with **E-CARGO Knowledge Agent**, an academic RAG assistant for authorised E-CARGO and Role-Based Collaboration literature. Retain the local Python/FastAPI/Bedrock/Titan/PostgreSQL/pgvector stack and Phase 0 infrastructure. Replace the Helpdesk business model, four tools, ticket drafts, and historical ticket retrieval with a two-tool literature MVP: `search_papers` and `get_paper_section`.
Reason: The portfolio project is now intended to answer research questions from reliable E-CARGO literature rather than provide enterprise IT support.
Consequences: ADR-002, ADR-003, and ADR-004 remain historical records but their Helpdesk-specific tool, ticket, and citation-write provisions are superseded for new implementation. No GMRA solving, optimisation, experiments, arbitrary code execution, or automatic model generation is permitted in the MVP. Existing Phase 0 infrastructure is retained; no database data or Docker volume is deleted.

## ADR-006 — 2026-11-02 — Truth-preserving Phase 1 metadata and page mapping
Status: Accepted (implementation decision)
Decision: Import user-provided PDFs by SHA-256 with physical PDF page index/number tracking. Do not infer bibliographic metadata from filenames, PDF body text, or unreliable PDF metadata: title, authors, year, venue, and DOI may remain null; `rights_status` defaults to `unknown`. Chunking is deterministic, page-bounded, and word-count approximate (350 words with 50-word overlap), not exact tokenisation. `printed_page_label` remains null until a reliable extractor is chosen.
Reason: Preserve source truth and citation integrity while allowing authorised sources whose embedded metadata is incomplete.

## ADR-007 — 2026-11-02 — Model-scoped local embedding baseline
Status: Accepted (Phase 2A implementation decision)
Decision: Use `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` as a local, 384-dimensional semantic-retrieval baseline. Store vectors in a new `chunk_embeddings` table keyed by `(chunk_id, model_id)`, with a persisted dimension, pgvector dimension constraint, and a partial HNSW cosine index for the local model. Keep the existing nullable `paper_chunks.embedding vector(512)` column untouched for a future, separately approved Titan Text Embeddings V2 configuration.
Reason: A 384-dimensional vector cannot safely be written to, padded into, or compared with the 512-dimensional Titan contract. Model-scoped persistence supports side-by-side evaluation without dimensional mixing.
Consequences: Query and corpus vectors must use the same `model_id`; semantic scores are cosine-derived ranking signals, not answer probabilities. Existing vectors for the same `(chunk_id, model_id)` are skipped on repeat runs. The Sentence Transformers package was verified at version 6.2.0; the Hugging Face model revision is not yet pinned, so reproducibility requires pinning a revision before production evaluation.

## ADR-008 — 2026-11-02 — Revision-scoped local embeddings
Status: Accepted (Phase 2A provenance correction)
Decision: Pin the local model to Hugging Face commit `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, verified from the local cache ref and Hugging Face model metadata. Add `model_revision` to `chunk_embeddings` and identify an embedding by `(chunk_id, model_id, model_revision)`. Preserve the earlier 178 rows with `model_revision = unknown`; generate a distinct 178-row pinned set rather than relabelling or overwriting legacy data.
Reason: Earlier rows did not record the resolved commit at generation time, so their exact model provenance cannot be proved retrospectively.
Consequences: Query retrieval filters by both model ID and revision. Legacy and pinned vectors cannot mix. Titan's future 512-dimensional vectors remain a separate model family.

## ADR-009 — 2026-11-02 — Offline structural grounding before a real LLM
Status: Accepted (Phase 3A implementation decision)
Decision: Implement evidence selection, provider abstraction, RAG orchestration, and structural citation validation using an explicitly non-generative local Mock provider. Citation validation accepts a citation only when its document/chunk/page agrees with both the request-scoped evidence and PostgreSQL.
Reason: This proves local contracts and prevents citation provenance failures without AWS access, paid services, or transmitting research text to a third party.
Consequences: `POST /api/v1/ask` is not a claim of real LLM quality or semantic grounding. A real provider requires separate user approval, and claim-level evidence support still requires evaluation/human review.
