# Project State — Update After Every Session

Last updated: 2026-11-02
Current phase: Phase 3A — Offline Grounded RAG orchestration complete. Phase 1 ingestion, Phase 1.5
inspection, and Phase 2A local retrieval remain verified. The ask flow has bounded evidence and structural
citation validation using a Mock provider; real LLM quality, Strands, Titan, Bedrock, and AWS remain
unimplemented/untested.

## Verified implementation

- Phase 0 remains verified: Python 3.12.16, Docker Compose, FastAPI `/health`, PostgreSQL 16.15, pgvector 0.8.7, pytest, and Ruff.
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
  validation checks request-scoped evidence and authoritative PostgreSQL document/chunk/page fields; and
  `POST /api/v1/ask` returns explicit `answered`, `insufficient_evidence`, or `provider_error` status.
  The Mock provider does not produce a scholarly conclusion and is never described as a real LLM.

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
  `backend/app/rag/`, `backend/alembic/`, `backend/tests/`, `evaluation/phase2a_retrieval_candidates.md`,
  `evaluation/phase2a_retrieval_review.md`, `docs/phase3a_grounded_rag_design.md`
- `.gitignore`, `README.md`, project Skill references, `DECISIONS.md`, and this file.

## Tests and checks

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
- Final Phase 3A local verification (2026-11-02): with a transient loopback `DATABASE_URL` constructed from
  existing local-only Compose variables, `pytest tests` reported **23 passed** (five upstream PyMuPDF SWIG
  warnings), `ruff check .` reported `All checks passed!`, and Alembic reported
  `0004_embedding_revision (head)`. A repeat embedding CLI run reported `processed=0`, `skipped=178`, and
  `failed=0`; it neither rewrote nor duplicated pinned vectors. No credential was printed or persisted.
- Local HTTP acceptance exercised `POST /api/v1/ask` with five corpus-related questions. It returned
  `answered`, `provider=mock`, and structurally valid citations for each; three intentionally unsupported
  questions (Mars-colony budget, World Cup 2026, quantum chromodynamics) returned
  `insufficient_evidence` with no selected citations. The response text is Mock evidence-review placeholder
  text, not an evaluation of real LLM answer quality. Swagger's OpenAPI page lists the `rag` group and
  `POST /api/v1/ask` locally.
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
  The Mock provider's output is evidence-review placeholder text, not an academic answer.

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
3. Choose a real LLM provider only with explicit cost/data approval; define its region, model ID, timeout,
   provider logging policy, and evaluation gate before implementing Phase 3B.

## Session handoff

Phase 3A has local ingestion, inspection APIs, 178 pinned 384-dimensional embeddings, 178 preserved
unknown-revision legacy embeddings, pgvector semantic retrieval, and Mock-backed structural grounding. It
does not have a real LLM, Strands Agent, chat/session persistence, structured section extraction, verified
bibliographic metadata, semantic citation-support evaluation, human relevance labels, Titan vectors, Bedrock
verification, or academic answer quality/citation readiness. Do not claim these unimplemented capabilities.

## Current blockers

- Git commands now fail before execution with `xcrun: error: invalid active developer path
  (/Library/Developer/CommandLineTools), missing xcrun at
  /Library/Developer/CommandLineTools/usr/bin/xcrun`. Therefore Phase 2A could not re-check `git status`,
  branch, or remote state after the earlier verified `origin/main` sync at `27b9f41`. No Git action was taken.
- Task 1 diagnostics on 2026-11-02 confirm `/Library/Developer/CommandLineTools` exists but its required
  `usr/bin/xcrun` does not; `/Applications/Xcode.app` is absent. `softwareupdate --list` offers Safari and
  macOS updates only, not a standalone Command Line Tools repair. The minimum safe repair now requires a
  user-driven Apple Command Line Tools/Xcode installation or repair; do not delete the existing CLT directory,
  run a system upgrade, or use sudo without explicit user action. Phase 2A commit/push is paused until Git
  works again.
- Docker Compose does not yet mount a persistent local Hugging Face model cache. Recreating the API container
  may therefore require another model-artifact download and adds startup/query latency; this is a local
  developer-experience limitation, not a corpus-data upload path.
