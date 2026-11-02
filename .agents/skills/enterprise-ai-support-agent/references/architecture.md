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
| Embedding | Titan Text Embeddings V2, 512-d | Literature/query vectors |
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
  -> Chat service (request-scoped agent + evidence registry)
  -> Strands Agent <-> Bedrock model
       | search_papers -> embedding service -> pgvector -> paper chunks
       | get_paper_section -> authorised source metadata + section/chunks
  -> Citation validator -> verified citations or abstention
  -> session/messages/retrieval audit metadata
```

## Academic corpus and ingestion

Ingest only material the user provides, is authorised to use, or is publicly usable. Do not put source documents in Git unless redistribution rights are confirmed.

1. Register `document_id`, title, authors, publication year, source/venue, document type, rights/provenance, and content hash.
2. Ingest PDF and Markdown while preserving originals in an authorised read-only mount.
3. Extract sections/text. Store page numbers only with a reliable original-PDF mapping; otherwise use section identity and null page metadata.
4. Chunk on headings and intact logical passages using deterministic IDs and content hashes.
5. Generate normalised Titan V2 512-dimensional embeddings; reject incorrect dimensions and avoid re-embedding unchanged chunks.
6. Upsert papers, sections, chunks, and vectors transactionally; re-ingestion must be idempotent and handle stale chunks.

## Retrieval and answer workflow

1. Receive question and session scope.
2. Generate a 512-dimensional query embedding matching ingestion configuration.
3. Use pgvector cosine distance to retrieve top-k chunks with document, section, text, score, and reliable page metadata.
4. Agent may call `get_paper_section` for bounded context; it must not call future/unimplemented tools.
5. Draft from evidence, distinguishing direct source claims from synthesis.
6. Validate citations against the request-scoped evidence registry.
7. Explicitly abstain when evidence is insufficient.

## Logical data model

- `papers(document_id PK, title NULL, authors JSONB NULL, publication_year NULL, publication_venue NULL, doi NULL, source_filename, rights_status, content_hash, page_count, created_at)`
- `paper_sections(section_id PK, document_id FK, heading, ordinal, page_start NULL, page_end NULL, content, content_hash)`
- `paper_chunks(chunk_id PK, document_id FK, section_id FK, chunk_ordinal, content, embedding vector(512), content_hash)`
- `chat_sessions(session_id UUID PK, created_at, updated_at)`
- `chat_messages(message_id UUID PK, session_id FK, role, content, created_at)`
- `retrieval_events(event_id UUID PK, session_id FK, query, evidence_ids JSONB, created_at)`

Use Alembic, foreign keys, indexes, transactions, and parameterised queries. Add ownership/auth fields before multi-user public deployment.

## Citation, safety, and operating boundaries

- A citation identifies an imported paper and section/chunk returned in the same request.
- Citation provenance is necessary but semantic support needs evaluation and human review.
- Page metadata is optional and never inferred from text position.
- Source text is untrusted input; it cannot invoke tools or override policy.
- Bound request length, tool calls, retrieval count, and model timeouts. Exclude secrets and unnecessary raw content from logs.
- Keep PostgreSQL on `127.0.0.1`; use ignored credentials. Bedrock calls require explicit approval and least privilege.

## Feasibility gates

- Local foundation: Python, Docker, API health, PostgreSQL, and pgvector are verified in `PROJECT_STATE.md`.
- AWS gate: Titan V2 512-d output and chosen model require approved live verification.
- Strands gate: installed SDK must complete the two-tool workflow in an approved real invocation.
- Academic RAG gate: ingestion, retrieval, citation validation, and abstention must pass evaluation before completion claims.
