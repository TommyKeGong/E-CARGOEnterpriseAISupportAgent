# Architecture Decision Log

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
