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

- Add approved Titan V2 512-dimensional embedding ingestion.
- Implement pgvector cosine top-k retrieval and request-scoped evidence metadata.
- Create authorised, fixed retrieval evaluation cases.

**Gate:** dimensions and retrieval metadata are verified; results include numerator/denominator.

## Phase 3 — E-CARGO Knowledge Agent

- Integrate one request-scoped Strands agent and approved Bedrock model.
- Implement/test `search_papers` and `get_paper_section` only.
- Implement chat sessions/messages and API contracts.

**Gate:** approved live invocation produces a validated cited answer; unsupported questions abstain. Record model, region, configuration, and cost evidence.

## Phase 4 — Citation Validation & RAG Evaluation

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
