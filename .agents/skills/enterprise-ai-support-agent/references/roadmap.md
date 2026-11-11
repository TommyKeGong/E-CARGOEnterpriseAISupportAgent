# E-CARGO Knowledge Agent — Roadmap, Acceptance Criteria & Evaluation v2.0

## Phase 0 — Local Development Foundation

**Status: local verification complete.** `PROJECT_STATE.md` records Python 3.12.16, dependencies, pytest, Ruff, Docker Compose, FastAPI `/health`, PostgreSQL 16.15, and pgvector 0.8.7. AWS and Bedrock are intentionally untested.

## Phase 1 — Academic Document Database & Ingestion

- Add SQLAlchemy, Psycopg, Alembic, and migrations.
- Define papers, sections, chunks, sessions/messages, and retrieval events.
- Ingest only authorised PDF/Markdown plus bibliographic metadata.
- Implement deterministic IDs, content hashes, reliable page mapping, chunking, and idempotent re-ingestion.

**Gate:** migration applies locally; a fixture corpus re-ingests twice without duplicates; metadata and page-null behaviour are tested. Do not download or fabricate papers.

## Phase 2 — Embeddings & Semantic Retrieval

- **Phase 2A — Local baseline: complete.** A local Sentence Transformers 384-dimensional model stores
  model-scoped vectors in `chunk_embeddings`; pgvector cosine top-k retrieval, idempotent generation,
  API inspection, migration, and tests are verified. This is retrieval only, not RAG answering.
- **Phase 2B — Titan comparison: planned and approval-gated.** Add approved Titan V2 512-dimensional
  embedding ingestion only after explicit AWS permission/cost approval. It must remain a distinct model
  family and evaluation configuration.
- Create authorised, fixed retrieval evaluation cases and human relevance labels before publishing quality
  metrics. Do not invent Recall@K, MRR, groundedness, or citation-validity results.

**Gate:** dimensions and retrieval provenance are verified; publish retrieval quality only with an
annotated denominator and numerator.

## Phase 3 — E-CARGO Knowledge Agent

- **Phase 3A — Grounded orchestration: complete locally.** Implement/test a retrieval-to-evidence-to-provider
  path, bounded evidence selection, structural citation validation, and `POST /api/v1/ask` with an explicitly
  labelled non-generative Mock provider. It runs without AWS credentials or a remote LLM.
- **Phase 3A.1 — Retrieval Transparency: complete locally.** Return selected persisted evidence text, physical
  page and retrieval score; optionally expose ranked Top-K audit results with selection reasons in local debug
  mode. Mock returns `evidence_retrieved` with no answer. This is inspection support, not real LLM quality or
  semantic-evidence validation.
- **Phase 3B — Ollama grounded generation: implemented and live-tested.** The optional Ollama provider,
  bounded context construction, strict JSON output parser, structural citation validation, configuration, and
  offline fake-provider tests are implemented. Loopback is default; an explicitly trusted private-network
  endpoint may receive selected evidence. A real invocation against a user-provided Ollama host and installed
  model returned a structurally valid cited answer. This is not semantic-grounding evaluation. Bedrock/Strands
  remain separately planned and approval-gated. Register only `search_papers` and `get_paper_section`; do not
  register future tools.
- Implement chat sessions/messages and persist retrieval/audit metadata.

**Gate:** an approved live invocation produces a structurally validated cited answer; unsupported questions
abstain. Record model, region, configuration, latency, and cost evidence. Structural citation validity alone
does not establish semantic grounding.

## Phase 4 — Citation Validation & RAG Evaluation

- **Phase 4A — Local document management: implemented and test-verified.** Bounded multipart PDF upload,
  existing transactional ingestion and pinned local embeddings, paginated document/chunk inspection, and
  transactional deletion are available for local/private use. No source-original persistence, authentication,
  or public exposure is included.
- **Phase 4B — Research tools foundation: implemented and test-verified.** A deterministic, read-only Python
  `ResearchTools` interface now exposes bounded document listing/detail/chunk reading, filtered pgvector paper
  search, and explicitly incomplete indexed page context. Only missing page-context aggregation gained an HTTP
  adapter; no autonomous tool calling, LLM orchestration, embedding change, or schema migration was introduced.
- **Phase 4C — Bounded research-agent orchestration: implemented and test-verified.** A fixed, validated tool
  registry supports request-scoped Ollama JSON actions and final answers under backend-enforced call, step,
  evidence, character, and time ceilings. It does not execute arbitrary model output; mock mode returns evidence
  without a scholarly answer. No migration, re-ingestion, model download, or live Ollama invocation was made.

- Enforce citation existence/provenance server-side.
- Evaluate groundedness, citation validity, abstention, retrieval quality, prompt-injection resistance, and errors.
- Report raw counts, failures, configuration, latency, and estimated cost.

**Gate:** publish numerator/denominator and review method; citation presence alone is not semantic proof.

## Phase 5 — Deployment & Portfolio Documentation

- Finalise Docker workflow, CI, README, architecture diagrams, and reproducible authorised demo process.
- Document setup, data-rights boundary, evaluation, and limitations.

**Gate:** fresh local setup reproduces documented non-AWS path. Public deployment needs separate security, auth, HTTPS, rights, and cost approval.

## Future Extension — GMRA Optimization Agent

Possible scope: validated inputs, PuLP/CBC solver execution, bounded resources, solution explanation, and evaluation. It requires a separate architecture, safety, dependency, and execution-policy decision before implementation.

## Session handoff

At session end update `PROJECT_STATE.md` with phase, changed files, exact commands/results, AWS/model status without secrets, blockers, decisions pending, and next three actions. New sessions read project instructions, Skill, references, state, decisions, and Git status before coding.
