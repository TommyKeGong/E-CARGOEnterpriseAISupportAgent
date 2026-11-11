# Project State — Update After Every Session

Last updated: 2026-11-10
Current phase: Phase 5A — Local React frontend foundation implemented and static-verified. Phase 4C.1 real
Ollama Agent verification remains incomplete and infrastructure-dependent; Phase 5B/public deployment remains
approval-gated.
Phase 1 ingestion, Phase 1.5 inspection, and Phase 2A local retrieval remain verified. The ask flow has
bounded evidence and structural citation validation using a Mock provider; real LLM quality, Strands, Titan,
Bedrock, and AWS remain unimplemented/untested.

## Current-session status (2026-11-10)

- Phase 4C.1 is **not passed**. Before this lightweight/static session, the approved private Ollama endpoint
  listed `qwen3:4b`, and one English Agent request returned a syntactically valid JSON `final` action before
  retrieval (`insufficient_evidence`, zero calls). The provider prompt was minimally changed to require an
  initial `search_papers` action. Subsequent real requests could not reach the local Docker PostgreSQL service
  after the machine restart, so English, Chinese, multiple-tool, and unsupported-question end-to-end Agent cases
  were not completed. The Qwen JSON action protocol is therefore unverified; do not claim the Agent is ready for
  live frontend use. No model was downloaded, corpus was re-ingested, migration applied, or database data changed.
- Phase 5A adds `frontend/`, a React + TypeScript + Vite + Tailwind local interface. Chat calls the actual
  `/api/v1/ask` and `/api/v1/agent/ask` contracts; Library calls existing document list/upload/detail/chunk/delete
  contracts; Sources calls the existing indexed page-context contract. It renders only response data and calls no
  non-existent PDF-download, arbitrary search, session, or tool-execution endpoint.
- Added a narrow development CORS configuration to FastAPI. `FRONTEND_ORIGINS` defaults to Vite loopback origins,
  avoids wildcard origins and browser credentials, and is not a public-deployment authorisation mechanism.
- This session deliberately did not start Docker Desktop/PostgreSQL/Ollama, perform live HTTP/LLM checks, run
  Alembic against a database, download an AI model, re-ingest papers, change schema, commit, or push.
- Static/offline checks run: `cd frontend && npm run build` (TypeScript + Vite production build passed),
  `cd frontend && npm run lint` (passed), `cd backend && .venv/bin/python -m pytest -q tests/test_health.py`
  (later 3 passed after the CORS-deny test was added; five upstream PyMuPDF SWIG deprecation warnings),
  `cd backend && .venv/bin/ruff check .` (passed), a static OpenAPI assertion for the six frontend-used route
  paths (passed), and `git diff --check` (passed). Full pytest, Alembic revision, database-backed route checks,
  browser E2E, CORS against a live process, and real Ollama Agent verification are unverified in this session.

### Frontend startup

1. Start the already-configured private backend separately when infrastructure verification is approved.
2. In `frontend/`, copy `.env.example` to ignored `.env.local`; set `VITE_API_BASE_URL` only if the backend
   uses a different private local origin.
3. Run `npm install` then `npm run dev`. The default Vite frontend origin is explicitly permitted by
   `FRONTEND_ORIGINS`; do not expose the unauthenticated backend publicly.

### Local service recovery (2026-11-10)

- After a machine restart, `curl http://127.0.0.1:8000/health` initially failed because Docker Compose had no
  running containers. Docker Desktop itself was healthy. `docker compose up -d --no-build` started the existing
  PostgreSQL and API containers without building, pulling, pruning, deleting, or changing any volume/model/data.
  PostgreSQL reported healthy and the follow-up health request returned HTTP 200 with `{"status":"healthy"}`.
- The running API image was created five days earlier. It restores the current local health endpoint, but it does
  not include workspace-only backend changes made after that image. Rebuilding it is intentionally deferred:
  the existing Dockerfile may acquire heavyweight ML dependencies/model artifacts and needs explicit resource
  review before doing so.

### Frontend fetch recovery (2026-11-10)

- The browser's `Failed to fetch` was reproduced as a CORS preflight failure: the old image returned HTTP 405 to
  `OPTIONS /api/v1/ask` and its OpenAPI specification lacked `/api/v1/agent/ask`. This was an image/source
  mismatch, not a retrieval, database, or Ollama failure.
- The old API container was stopped without deleting it or touching the healthy database container/volume. The
  current workspace source now runs locally on `127.0.0.1:8000` in `RAG_PROVIDER=mock` and `HF_HUB_OFFLINE=1`
  mode, with the existing private PostgreSQL service. Its CORS preflight from `http://localhost:5173` returns
  HTTP 200 and the explicit allow-origin header; OpenAPI contains both `/api/v1/ask` and `/api/v1/agent/ask`.
- Actual same-origin-style POST checks from `http://localhost:5173` passed: `/api/v1/ask` returned HTTP 200,
  `evidence_retrieved`, provider `mock`, three evidence items and three citations; `/api/v1/agent/ask` returned
  HTTP 200, `evidence_retrieved`, provider `mock`, one tool call, and five evidence items. No remote Ollama
  request, model download, corpus mutation, migration, commit, or push occurred.

### Approved Ollama web-mode enablement (2026-11-10)

- Following explicit user approval, the current source API on `127.0.0.1:8000` was restarted with the already
  approved private Ollama endpoint, `qwen3:4b`, 120-second timeout, and exact-match trusted endpoint setting.
  These values exist only in the running process environment and were not written to `.env` or source control.
  A read-only `/api/tags` check confirmed the already-installed model; no model was downloaded.
- Real browser-equivalent RAG request `What is E-CARGO?` returned HTTP 200 with `status=answered`, provider
  `ollama`, two selected evidence items, one validated citation to `Computational Thinking.pdf` physical page 4,
  and `invalid_citation_count=0`. The returned sentence was inspected only for the structural contract; citation
  validity remains provenance validation, not proof of semantic entailment.
- Real browser-equivalent Agent request for the same question returned HTTP 200 with `status=answered`, provider
  `ollama`, one `search_papers` tool call, one evidence item, one matching page-4 citation,
  `invalid_citation_count=0`, and 44,574 ms reported execution time. It used strict JSON action flow (tool then
  final) for this case. Chinese, multi-tool, unsupported-question, timeout, and malformed-output live cases are
  still unverified, so Phase 4C.1 remains incomplete.

## Verified implementation

- Phase 0 remains verified: Python 3.12.16, Docker Compose, FastAPI `/health`, PostgreSQL 16.15, pgvector 0.8.7, pytest, and Ruff.
- Phase 4C bounded research agent (2026-11-06): added `app.rag.agent.BoundedResearchAgent` and
  `POST /api/v1/agent/ask`. It permits only the five existing Phase 4B read-only tools and validates each
  structured JSON action plus its Pydantic arguments before execution. Backend limits cap calls (5), steps (8),
  evidence items (15), cumulative tool-result characters (20,000), and time (180 seconds); environment values
  may tighten but not raise those ceilings. Request-scoped evidence feeds the existing structural citation
  validator. The Mock provider retrieves evidence but deliberately returns no scholarly answer. No tool can
  execute arbitrary code, shell, SQL, filesystem, network, or write operations; document text is untrusted data.
- Phase 4B research-tools foundation (2026-11-06): added route-independent `ResearchTools` operations for
  bounded `search_papers`, one-based paginated `list_papers`/`read_chunks`, `get_document`, and
  `get_page_context`. It delegates semantic search to the same pinned local pgvector retrieval and validates all
  supplied document filters against persisted documents. Results preserve document/chunk/source filename/physical
  page provenance; no tool accepts filesystem paths, arbitrary SQL, shell input, writes, or network actions.
  `get_page_context` joins only persisted chunks mapped to a physical page and always says it is not the original
  complete PDF page. The only new read-only HTTP adapter is
  `GET /api/v1/documents/{document_id}/pages/{pdf_page_number}/context`; valid text-empty pages return an empty,
  explicitly incomplete context. No migration, embedding-model change, corpus re-ingestion, Ollama request, or
  document deletion occurred.
- Added SQLAlchemy 2.1.6, Psycopg 3.3.6, Alembic 1.20.1, pgvector 0.5.1, and PyMuPDF 2.1 to `backend/.venv`.
- Alembic revisions `0001_academic_corpus` and `0002_authors_jsonb` are applied. They create non-destructive `papers`, `paper_sections`, and `paper_chunks` tables plus pgvector extension/indexes and align `authors` with the JSONB contract; downgrade is disabled intentionally.
- Implemented `AcademicDocument`, `DocumentSection`, `DocumentChunk`; the original nullable
  `paper_chunks.embedding vector(512)` remains unused and unchanged. Local Phase 2A embeddings reside only
  in model-scoped `chunk_embeddings` rows.
- Implemented local PyMuPDF extraction, physical PDF page mapping, deterministic page-bounded word-count approximation (350 words, 50 overlap), SHA-256 duplicate protection, transaction flush, and local CLI ingestion.
- Imported two user-provided local PDFs without changing them:
  - `Computational Thinking.pdf`: SHA-256 `06b2c74db5a2ff9e0cc9909e320354e65377ed094ae091149ffddf7daddddf78`; 8 PDF pages; 21 chunks; page 8 has no extractable text.
  - `Thsis.pdf`: SHA-256 `270eb5b15b6c2e09c5a75ef11b3e7a5d9afaef64a3c97c71d301ed54573f2467`; 157 PDF pages; 157 chunks; all pages produced text.
- Re-import returned `duplicate_skipped` for both documents. Database validation: 2 documents, 178 chunks, 0 empty chunks, 0 invalid page mappings, 0 replacement-character chunks, and 0 duplicate content hashes.
- Added local read-only inspection APIs backed by SQLAlchemy/Pydantic v2: paper list, paper detail,
  chunk pagination, and bounded PostgreSQL `ILIKE` keyword search. The keyword endpoint is explicitly not
  semantic search or RAG, and API routes issue `SELECT` queries only.
- Safely rebuilt only the Docker Compose `api` service. PostgreSQL remained healthy and its named volume was
  not deleted or recreated. HTTP verification returned `/health`, two paper records (8/21 and 157/157
  pages/chunks), and two bounded `E-CARGO` keyword matches.
- Phase 1.5 acceptance re-verified the running local stack without rebuilding it: both Compose services are
  healthy, Swagger exposes all four paper-inspection routes, and HTTP checks returned 200 for paper detail and
  chunk pagination, 404 for an unknown document, and 422 for an empty keyword query.
- Applied non-destructive Alembic revision `0003_chunk_embeddings`. It creates `chunk_embeddings` with
  `embedding_id`, `chunk_id` FK, `model_id`, `dimension`, `embedding`, `created_at`, uniqueness on
  `(chunk_id, model_id)`, a dimension/vector check constraint, and a local-model-only HNSW cosine index.
  It neither changes `paper_chunks.embedding vector(512)` nor deletes corpus data.
- Implemented the local baseline `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` through
  `sentence-transformers` 6.2.0. The model reports 384 dimensions. Validation rejects wrong dimensions,
  NaN, and infinity. The first download obtained public model artifacts from Hugging Face only; PDF and chunk
  text were not uploaded.
- Generated vectors for all 178 persisted chunks. Database validation recorded 178 rows for the local model,
  dimensions min/max 384, zero vector-dimension mismatches, and zero chunks missing a local vector. A
  repeat CLI run processed 0, skipped 178, and failed 0 in 0.076 seconds, so it did not create duplicate
  embeddings.
- Implemented `GET /api/v1/papers/semantic-search` with Pydantic v2 response models. It embeds a query with
  the same local model and asks PostgreSQL pgvector to cosine-rank only matching `model_id` rows; no corpus
  vectors are loaded into Python for similarity computation. Results carry document, filename, chunk ID,
  physical PDF page, bounded excerpt, and a ranking score. This endpoint is Semantic Retrieval, not keyword
  search, answer generation, confidence scoring, or Agentic RAG.
- Docker Compose API was safely rebuilt/recreated after the first build completed; only the API container was
  replaced. The PostgreSQL container stayed healthy and its named volume was not deleted or recreated.
  OpenAPI/Swagger now lists `/api/v1/papers/semantic-search` and its parameter schema.
- Applied non-destructive Alembic revision `0004_embedding_revision`. It adds `model_revision`, records all
  pre-existing vectors as `unknown`, replaces the uniqueness constraint with `(chunk_id, model_id,
  model_revision)`, and adds a lookup index. It does not delete or rewrite any vector values.
- Hugging Face local cache `refs/main` and the official model metadata both returned
  `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` for
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. The encoder is now pinned to that revision.
  Because the initial 178 vectors did not persist a revision at creation time, they remain correctly labelled
  `unknown`; they were not retroactively marked as pinned.
- Generated and validated a separate pinned revision corpus: 178 vectors, dimensions min/max 384, zero pinned
  chunks missing vectors. The database contains 356 local vectors total: 178 `unknown` legacy rows and 178
  pinned rows. Retrieval filters on model ID and revision, so they cannot mix.
- Implemented Phase 3A modules: semantic retrieval is passed to bounded exact-duplicate-removing evidence
  selection; the provider interface defaults to an offline, non-generative `mock`; structural citation
  validation checks request-scoped evidence and authoritative PostgreSQL document/chunk/page fields. Phase
  3A.1 supersedes the earlier Mock status semantics; it does not produce a scholarly conclusion or an answer.
- Phase 3A.1 corrects the Mock semantics: it now returns `status="evidence_retrieved"` and `answer=null`.
  `answered` remains reserved for a future real provider that generated an answer. The response exposes
  selected local `evidence` with its authoritative document/chunk/source/page provenance, full persisted
  chunk text, actual pgvector similarity score, and `selected=true`.
- Optional `debug_retrieval=true` returns every requested Top-K candidate in rank order, including its full
  persisted text, score, selected flag, and the actual selector reason. Debug is off by default and must stay
  local-development-only; it is not logged. Current selector reasons are `selected`,
  `below_minimum_similarity`, `duplicate_chunk_text`, `evidence_character_budget_exhausted`, and
  `max_evidence_reached`.
- Confirmed database state before Phase 3A.1 acceptance: 2 documents and 178 chunks. Existing embeddings and
  database data were not regenerated, overwritten, or deleted.

## Metadata and parsing limitations

- Both PDFs lack a reliable embedded title. No title, authors, publication year, venue, DOI, printed page label, or inferred citation was fabricated; those fields remain null and `rights_status` is `unknown`.
- PyMuPDF yielded plain text only. No automatic detection/repair of complex columns, formulas, or tables is implemented. The empty page in `Computational Thinking.pdf` may be scanned/visual content and needs human review.
- A beginning/middle/end PyMuPDF sample confirmed 4,490/5,729/0 extracted characters on pages 1/5/8 of
  `Computational Thinking.pdf`, and 333/1,077/1,397 characters on pages 1/79/157 of `Thsis.pdf`. No
  replacement-character pages were found. `page.find_tables()` found no table candidates in those samples;
  this does not prove tables are absent. Formula-like characters were absent in the sampled first PDF pages;
  the 28 formula-like lines on the final `Thsis.pdf` page were code-like equality expressions, not a reliable
  mathematical-formula extraction. Block ordering from plain text is not evidence that multi-column reading
  order, formulas, or visual tables are correct.
- Chunk page mapping remains within extracted content: `Computational Thinking.pdf` covers physical pages 1–7
  in 21 chunks (page 8 is text-empty), while `Thsis.pdf` covers pages 1–157 in 157 chunks.
- Chunk sizes are approximate words, not exact model tokens. Sections are schema-supported but no reliable heading/section parser has yet populated them.

## Files changed

- `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/db.py`, `backend/app/models.py`,
  `backend/app/schemas.py`
- `backend/app/ingestion/`, `backend/app/embeddings/`, `backend/alembic.ini`, `backend/alembic/`,
  `backend/app/rag/`, `backend/app/research_tools.py`, `backend/alembic/`, `backend/tests/`,
  `evaluation/phase2a_retrieval_candidates.md`,
  `evaluation/phase2a_retrieval_review.md`, `docs/phase3a_grounded_rag_design.md`
- `.gitignore`, `README.md`, project Skill references, `DECISIONS.md`, and this file.

## Tests and checks

- Phase 4C bounded agent (2026-11-06): added `backend/tests/test_agent.py` using scripted/fake providers and
  local transactional fixtures. It covers valid tool/citation flow, multiple-call limits, unknown tool,
  invalid arguments, empty evidence, invalid citations, provider unavailable, execution timeout, Chinese question
  preservation, untrusted prompt-text handling, and the Mock-backed HTTP route. Focused checks:
  `pytest -q tests/test_agent.py` **10 passed**; targeted Ruff passed. Final full checks:
  `pytest -q tests` **54 passed** with five upstream PyMuPDF SWIG
  deprecation warnings; `ruff check .` passed; Alembic reports `0004_embedding_revision (head)`. The database
  test URL was transiently built from the running private Compose database environment and was never printed or
  persisted. No live Ollama Phase 4C invocation was made.

- Phase 4B research tools (2026-11-06): added `backend/tests/test_research_tools.py` with fake local embeddings
  and database savepoint rollback coverage for source/chunk/page metadata integrity, document-filtered search,
  pagination, invalid document IDs, a valid-but-text-empty page, page bounds, and the read-only page-context HTTP
  adapter. It also confirms an indexed document with no persisted vectors returns an empty semantic-search result.
  Focused checks passed: `pytest -q tests/test_research_tools.py` **4 passed** with five upstream PyMuPDF SWIG
  deprecation warnings; targeted `ruff check` passed. Final full checks: `pytest -q tests` **44 passed** with
  five upstream PyMuPDF SWIG deprecation warnings; `ruff check .` passed; Alembic reports
  `0004_embedding_revision (head)`. The database test URL was transiently built from the running private Compose
  database environment and was never printed or persisted.

- Phase 4A document management (2026-11-06): implemented bounded multipart PDF upload, SHA-256 duplicate
  detection, existing transactional PyMuPDF ingestion, pinned local embedding generation, paginated document
  and chunk inspection, page-number filtering, detail/index status, and transactional document deletion. The
  upload route validates a plain `.pdf` name, `application/pdf` type, configurable
  `DOCUMENT_UPLOAD_MAX_BYTES` (25 MiB default), PDF signature, and parser result. It stages only an
  OS-managed temporary file and always removes it. A failed embedding run rolls the document/chunks/vectors
  back; no schema migration was needed.
- Added `backend/tests/test_documents_api.py`. It uses per-request savepoints inside an outer test transaction,
  so valid-upload, duplicate, listing/detail, chunk filtering, deletion, invalid/empty/malformed/oversized
  uploads, missing deletion, and embedding-failure rollback do not modify the two existing corpus documents.
  Final checks: `pytest -q tests` **40 passed** with five upstream PyMuPDF SWIG deprecation warnings;
  `ruff check .` passed; Alembic reports `0004_embedding_revision (head)`.

- Phase 3B remote Ollama integration (2026-11-06): user authorised a private-network Ollama endpoint with an
  installed `qwen3:4b` model. A no-corpus `GET /api/tags` probe confirmed it was reachable and listed both
  `qwen3:4b` (2,497,293,931 bytes) and `qwen3:8b`; no model was downloaded. A temporary local Uvicorn API
  used `RAG_PROVIDER=ollama`, the configured model, a 120-second timeout, and the exact-match trusted endpoint
  acknowledgement. A real `POST /api/v1/ask` question, `What is the E-CARGO model?`, returned HTTP 200 with
  `status=answered`, provider `ollama`, three selected local evidence chunks, one citation, and
  `invalid_citation_count=0`. The citation matched selected evidence exactly: `Computational Thinking.pdf`,
  page 4, and its document/chunk identifiers. The observed end-to-end response time was approximately 52
  seconds, including first local embedding-model load. The generated answer was inspected but is not a
  semantic-grounding or answer-quality evaluation. The temporary API was stopped after the check.
- Phase 3B configuration hardening (2026-11-06): non-loopback Ollama URLs are no longer broadly allowed.
  They must exactly equal `OLLAMA_TRUSTED_BASE_URL`; loopback remains the default. This keeps model endpoint
  and consent out of application logic while requiring explicit acknowledgement before selected evidence is
  transmitted to another host. No database migration, corpus/embedding operation, AWS call, or Git write was
  performed.
- Added fake-requester coverage for Chinese question preservation and exact non-loopback endpoint trust, in
  addition to normal generation, unavailable service, timeout, missing model, malformed output, empty
  retrieval/abstention, unsupported citations, and Mock regression. Final checks: `pytest -q tests` **35
  passed** with five upstream PyMuPDF SWIG deprecation warnings; `ruff check .` passed; Alembic reports
  `0004_embedding_revision (head)`.

- Phase 3A.1 final acceptance (2026-11-05): with the database service healthy, a temporary local Uvicorn
  process was run in Hugging Face offline mode on `127.0.0.1:8010`; it could not download a model. Two real
  HTTP `POST /api/v1/ask` requests for `What is the E-CARGO model?` returned HTTP 200 from the `mock`
  provider with `status=evidence_retrieved` and `answer=null`. The debug request returned three selected
  persisted evidence chunks and five ranked candidates. The unselected page-8 and page-5 candidates had the
  factual `evidence_character_budget_exhausted` reason. The non-debug request returned `debug_retrieval=null`
  and no unselected evidence. All three response citations matched the selected evidence and direct
  PostgreSQL lookup exactly: document/chunk/source/page pairs were `Computational Thinking.pdf` page 4,
  `Thsis.pdf` page 9, and `Thsis.pdf` page 27. The temporary API was stopped after validation.
- Phase 3B local preparation (2026-11-05): added a local loopback-only `OllamaProvider` in
  `backend/app/rag/providers.py`, selected only by `RAG_PROVIDER=ollama`; `mock` remains the default.
  `OLLAMA_MODEL` is required and no model name is embedded in business logic. Bounded selected evidence is
  formatted as untrusted data, the provider requests JSON answer/citation output, and its output still passes
  the request-scoped/PostgreSQL structural citation validator. Empty answer plus no citations is a controlled
  insufficient-evidence abstention; unavailable service, timeout, missing model, empty answer with citations,
  and malformed output are controlled provider errors. No schema, embedding, corpus, or cloud-service change
  was made.
- Added fake-requester unit coverage for normal structured generation, no-evidence rejection, timeout,
  unavailable service, missing model, empty abstention, empty answer with citations, malformed output,
  invalid citation shape, provider selection, document/page citation mismatch, and Mock regression. With the
  transient local test `DATABASE_URL`, `backend/.venv/bin/pytest -q tests` passed: **33 passed, 5 upstream
  PyMuPDF SWIG deprecation warnings**; `backend/.venv/bin/ruff check .` passed; Alembic reported
  `0004_embedding_revision (head)`. These tests did not require or contact Ollama.
- Resource assessment (read-only, 2026-11-05): host is Apple Silicon (`arm64`) with 16 GiB RAM and about
  15 GiB available on the system volume. The project directory uses 1.4 GiB, Hugging Face cache uses 458 MiB,
  Ollama is not installed and its cache is absent. Docker reports 20.24 GB images, 20.76 GB build cache, and
  67.15 MB volumes; nothing was cleaned. Disk headroom is limited for a local LLM download.
- Current Phase 3B next steps: (1) obtain user approval before installing Ollama or downloading any model;
  (2) if approved, start with the user-selected small local model and configure `RAG_PROVIDER=ollama` plus
  `OLLAMA_MODEL`; (3) run a separately recorded live local integration test for valid citation generation,
  abstention, timeout/unavailable service, and invalid-citation rejection. Do not treat a successful live
  invocation or structural citation validation as proof of semantic grounding.

- Crash-recovery verification (2026-11-05): the local `db` Compose service had stopped and port 5432
  refused connections after the workstation crash. It was restored with `docker compose up -d db` only;
  the existing two-day-old database container and its named volume were reused, not recreated or deleted.
  `docker compose ps db` then reported `healthy`. With a transient loopback `DATABASE_URL` constructed
  from the existing local Compose variables (and never printed or persisted), `backend/.venv/bin/pytest -q
  tests` passed: **26 passed, 5 upstream PyMuPDF SWIG deprecation warnings**. `backend/.venv/bin/alembic
  -c alembic.ini current` reported `0004_embedding_revision (head)`, and `backend/.venv/bin/ruff check .`
  reported `All checks passed!`. No migration, corpus, embedding, or source-file change was made.
- An initial post-crash test run without `DATABASE_URL` produced four database API failures and twelve
  skipped database tests; this was corrected by the transient local test configuration above and was not a
  code regression.

- Alembic `upgrade head` and `current`: passed; current revision `0002_authors_jsonb`; PostgreSQL confirms `papers.authors` is `jsonb`.
- `pytest`: 13 passed. PyMuPDF emits 5 upstream SWIG deprecation warnings; no test failures.
- `ruff check .`: passed.
- Phase 1.5 recheck: `pytest` 13 passed; `ruff check backend` passed; Alembic reports
  `0002_authors_jsonb (head)`.
- Phase 2A: `backend/.venv/bin/alembic -c alembic.ini upgrade head` and `current` passed; current revision is
  `0003_chunk_embeddings (head)`. `backend/.venv/bin/python -m pytest backend/tests` passed: **18 passed**
  (five upstream PyMuPDF SWIG deprecation warnings). `backend/.venv/bin/ruff check backend` passed.
- A final test attempt that merely sourced root `.env` failed with four database API tests, eight passes, six
  skips, and an Alembic `KeyError: 'DATABASE_URL'`; root `.env` intentionally does not define that test-only
  loopback URL. Re-running with an in-process `DATABASE_URL` built from the existing local
  `POSTGRES_PASSWORD` passed: **18 passed, 5 warnings**, Ruff `All checks passed!`, and Alembic
  `0003_chunk_embeddings (head)`. No credentials were printed or saved.
- Phase 2A unit/integration coverage includes vector dimension and finite-value validation, batch/idempotent
  generation, semantic ranking and document filtering, empty/invalid query validation, missing-model and
  database-error responses, plus the pre-existing inspection/ingestion regression suite.
- Phase 3A: Alembic reports `0004_embedding_revision (head)`; pytest reports **23 passed** with five upstream
  PyMuPDF SWIG deprecation warnings; Ruff passes after formatting. New tests cover bounded duplicate evidence,
  no results, low-score unsupported retrieval, valid and hallucinated citation handling, provider timeout,
  provider-error status, empty/invalid ask requests, and existing API regression.
- Phase 3A.1: `pytest tests` reports **26 passed** with five upstream PyMuPDF SWIG deprecation warnings;
  `ruff check .` passes; Alembic reports `0004_embedding_revision (head)`. Added coverage verifies Mock
  `evidence_retrieved`/null-answer semantics, source-text and page preservation, citation/evidence alignment,
  selector audit reasons, debug enable/disable behavior, rank serialization, and existing API validation.
- Final Phase 3A local verification (2026-11-02): with a transient loopback `DATABASE_URL` constructed from
  existing local-only Compose variables, `pytest tests` reported **23 passed** (five upstream PyMuPDF SWIG
  warnings), `ruff check .` reported `All checks passed!`, and Alembic reported
  `0004_embedding_revision (head)`. A repeat embedding CLI run reported `processed=0`, `skipped=178`, and
  `failed=0`; it neither rewrote nor duplicated pinned vectors. No credential was printed or persisted.
- Earlier Phase 3A HTTP acceptance used the now-superseded Mock response shape. Phase 3A.1 uses
  `evidence_retrieved` with `answer: null` instead; the new local API acceptance is recorded separately in
  this session's Phase 3A.1 results.
- Swagger/OpenAPI verification after the API-only rebuild: `GET /openapi.json` lists
  `/api/v1/papers/semantic-search`; an actual local request for `What is the E-CARGO model?` returned 200 and
  three provenance-bearing results. Swagger UI itself was used with `q=What is the E-CARGO model?` and
  `top_k=3`, returning HTTP 200 and the same three local results. Five actual semantic-query Top-3 result
  sets were recorded below.
- Docker API rebuild plus HTTP checks: passed after the API process finished starting. Swagger/OpenAPI is
  available locally at `http://127.0.0.1:8000/docs`.
- Original PDF inspection used PyMuPDF only; PDFs were not uploaded or modified.
- No AWS, Bedrock, Titan, Strands, Git commit/push, Docker Volume rebuild, or data deletion occurred during
  the earlier Phase 1/1.5 work.
- No AWS, Bedrock, Titan, Strands, Git commit/push, raw-PDF mutation/upload, Docker Volume rebuild, or data
  deletion occurred in Phase 2A. The only external download was the explicitly local-model package/artifact
  acquisition from PyPI/Hugging Face; corpus text was not sent externally.

## Phase 2A retrieval observations (not quality metrics)

Actual local `top_k=3` pgvector results, shown as `source filename / physical PDF page / score`:

- `What is the E-CARGO model?`: `Computational Thinking.pdf / 4 / 0.6606`; `Thsis.pdf / 9 / 0.5850`;
  `Thsis.pdf / 27 / 0.5763`.
- `What is Role-Based Collaboration?`: `Computational Thinking.pdf / 4 / 0.7529`; `Thsis.pdf / 23 / 0.6847`;
  `Thsis.pdf / 25 / 0.6671`.
- `How are agents assigned to roles?`: `Thsis.pdf / 31 / 0.7026`; `Computational Thinking.pdf / 4 / 0.6763`;
  `Thsis.pdf / 11 / 0.6633`.
- `What is an E-CARGO environment?`: `Thsis.pdf / 27 / 0.7207`; `Computational Thinking.pdf / 4 / 0.6977`;
  `Thsis.pdf / 8 / 0.5018`.
- `How does E-CARGO support decision making?`: `Thsis.pdf / 9 / 0.7126`; `Thsis.pdf / 8 / 0.5699`;
  `Computational Thinking.pdf / 4 / 0.5666`.

These are retrieval observations, not manually adjudicated evidence support. The ten query/concept candidates
in `evaluation/phase2a_retrieval_candidates.md` were confirmed to have one or more keyword matches, but a
human reviewer must label relevant chunks before Recall@K, MRR, or a Keyword-vs-Semantic performance claim.

## Retrieval review and Phase 3A limitations

- Ran ten real corpus-related questions through both Keyword and fixed-revision Semantic retrieval. The full
  Top-5 provenance/excerpt record and automatic preliminary observations are in
  `evaluation/phase2a_retrieval_review.md`. Several full natural-language phrases had no exact `ILIKE` hit but
  semantic results had topical language; this is an observation, not a measured advantage. Bibliography and
  table-of-contents matches are explicitly flagged as possible keyword noise.
- No reviewer has supplied relevance or claim-support labels. No Recall@K, MRR, precision, groundedness, or
  answer-accuracy figure exists.
- `POST /api/v1/ask` is structurally grounded only. It checks citation provenance, not semantic entailment.
  The Mock provider returns selected evidence with no academic answer.
- The Phase 3A.1 review in `evaluation/phase3a1_evidence_review.md` records actual Top-5 pgvector results for
  eight E-CARGO/RBC questions, selected/unselected state, source pages, scores, exact stored-text excerpts,
  and automatic preliminary observations. It is not human annotation and reports no retrieval or answer metric.

## Publication readiness

- Expanded `.gitignore` to protect `.env.*` while retaining `.env.example`, `kb/processed/`, local
  PostgreSQL data/backups, local SQLite files, common AWS credential directories, and private-key file
  extensions. Existing rules already exclude `kb/raw/`, virtual environments, Python bytecode, and test/lint
  caches.
- A filename-only sensitive-pattern scan outside ignored corpus/cache directories found only `.env.example`,
  which contains placeholders. No source PDF was read, staged, or published.
- Git is verified as `git version 2.54.0 (Apple Git-157)`. SSH authentication through the local
  `github-tommy` alias is verified as `TommyKeGong`; `origin` uses that alias for the specified private GitHub
  repository.
- Final staged-file checks covered 33 files. `git diff --cached --check` passed; prohibited PDF, `.env`,
  database, cache, virtual-environment, and private-key artifacts were absent. The only case-insensitive
  credential-field match was placeholder-only `.env.example`, whose values were redacted for review.
- The remote's existing, empty-tree history (`969bce9 Initial commit`, `1a91ae3 Delete README.md`) was
  explicitly preserved by an authorised non-destructive unrelated-history merge. No force push, remote-branch
  deletion, data deletion, or PDF publication occurred.
- Published initial project commit `c85a64a feat: initialize E-CARGO Knowledge Agent with PDF ingestion`
  (33 files) and merge commit `0ab8d4e` to private `origin/main` with an ordinary `git push -u origin main`.

## Blockers / next three actions

1. Obtain authorised bibliographic metadata for the two PDFs (or confirm that null metadata is acceptable for
   the fixture corpus) and decide a reliable section/printed-page-label extraction policy.
2. Have a qualified reviewer label `evaluation/phase2a_retrieval_review.md`, including topical relevance,
   bibliography/table-of-contents noise, and claim-level support before publishing metrics.
3. Before Phase 5 or any public/frontend exposure, obtain explicit approval for authentication, authorisation,
   rights-aware text policy, reproducible evaluation, and deployment security. Do not treat citation provenance
   as semantic entailment or expose the unauthenticated local APIs.

## Session handoff

Phase 4C has local ingestion/document management, 178 pinned 384-dimensional embeddings, 178 preserved
unknown-revision legacy embeddings, pgvector semantic retrieval, structural citation validation, optional private
Ollama generation, deterministic read-only `ResearchTools`, and bounded request-scoped research-agent
orchestration. It does not have persisted sessions/audit events, structured section extraction, verified
bibliographic metadata, semantic citation-support evaluation, human relevance labels, Titan vectors, Bedrock
verification, or academic answer-quality/citation readiness. Do not claim these unimplemented capabilities.

## Current blockers

- Docker Compose does not yet mount a persistent local Hugging Face model cache. Recreating the API container
  may therefore require another model-artifact download and adds startup/query latency; this is a local
  developer-experience limitation, not a corpus-data upload path.
- The document-management and page-context endpoints remain unauthenticated local/private interfaces. A future
  frontend or network deployment needs authentication, authorisation, rights-aware content exposure, and a
  separate security review.
