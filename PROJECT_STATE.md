# Project State — Update After Every Session

Last updated: 2026-11-02
Current phase: Phase 1 — Academic Document Database & Ingestion in progress. Schema, PDF ingestion,
two authorised local PDFs, and local read-only acceptance APIs are verified; embeddings/retrieval are not
implemented.

## Verified implementation

- Phase 0 remains verified: Python 3.12.16, Docker Compose, FastAPI `/health`, PostgreSQL 16.15, pgvector 0.8.7, pytest, and Ruff.
- Added SQLAlchemy 2.1.6, Psycopg 3.3.6, Alembic 1.20.1, pgvector 0.5.1, and PyMuPDF 2.1 to `backend/.venv`.
- Alembic revisions `0001_academic_corpus` and `0002_authors_jsonb` are applied. They create non-destructive `papers`, `paper_sections`, and `paper_chunks` tables plus pgvector extension/indexes and align `authors` with the JSONB contract; downgrade is disabled intentionally.
- Implemented `AcademicDocument`, `DocumentSection`, `DocumentChunk`; embedding is nullable `vector(512)` and no embeddings were generated.
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

## Metadata and parsing limitations

- Both PDFs lack a reliable embedded title. No title, authors, publication year, venue, DOI, printed page label, or inferred citation was fabricated; those fields remain null and `rights_status` is `unknown`.
- PyMuPDF yielded plain text only. No automatic detection/repair of complex columns, formulas, or tables is implemented. The empty page in `Computational Thinking.pdf` may be scanned/visual content and needs human review.
- Chunk sizes are approximate words, not exact model tokens. Sections are schema-supported but no reliable heading/section parser has yet populated them.

## Files changed

- `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/db.py`, `backend/app/models.py`,
  `backend/app/schemas.py`
- `backend/app/ingestion/`, `backend/alembic.ini`, `backend/alembic/`, `backend/tests/`
- `.gitignore`, `README.md`, project Skill references, `DECISIONS.md`, and this file.

## Tests and checks

- Alembic `upgrade head` and `current`: passed; current revision `0002_authors_jsonb`; PostgreSQL confirms `papers.authors` is `jsonb`.
- `pytest`: 13 passed. PyMuPDF emits 5 upstream SWIG deprecation warnings; no test failures.
- `ruff check .`: passed.
- Docker API rebuild plus HTTP checks: passed after the API process finished starting. Swagger/OpenAPI is
  available locally at `http://127.0.0.1:8000/docs`.
- Original PDF inspection used PyMuPDF only; PDFs were not uploaded or modified.
- No AWS, Bedrock, Strands, embeddings, external downloads, Git commit, Docker Volume rebuild, or data deletion occurred.

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

1. Obtain authorised bibliographic metadata for the two PDFs (or confirm that null metadata is acceptable for the fixture corpus) and decide a reliable section/printed-page-label extraction policy.
2. Complete remaining Phase 1 section extraction and metadata-validation workflow, including explicit authorised metadata input.
3. After explicit AWS cost approval and credentials, begin Phase 2 with Titan V2 512-d embeddings and pgvector retrieval evaluation.

## Session handoff

Phase 1 has a working local ingestion foundation and read-only inspection APIs but is not complete: no embeddings,
semantic retrieval, Agent, structured section extraction, verified bibliographic metadata, answer generation, or
citation validation exists. Do not claim academic answer quality or citation readiness.
