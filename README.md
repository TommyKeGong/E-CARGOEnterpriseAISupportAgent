# E-CARGO Knowledge Agent

An agentic RAG research assistant for E-CARGO and Role-Based Collaboration (RBC). The MVP answers research questions only from authorised academic literature, with validated citations and explicit abstention when evidence is insufficient.

## Scope

The intended corpus covers RBC, E-CARGO, GRA, GMRA, mathematical formulations, role-assignment algorithms, and documented applications including immigration policy simulation, clinical therapy planning, and scheduling. Sources must be user-provided, authorised, or publicly usable. This repository neither automatically downloads papers nor publishes restricted documents.

The MVP excludes GMRA solving, optimisation, experiment execution, arbitrary code execution, and automatic mathematical-model generation.

## Current status

Phase 2A is complete as a local retrieval baseline. The local academic corpus contains two user-provided PDFs and 178 extracted chunks. PostgreSQL 16 + pgvector stores 178 model-scoped, 384-dimensional local embeddings. The app provides read-only corpus inspection, PostgreSQL `ILIKE` keyword search, and pgvector cosine semantic search. It does not provide RAG answers, citations, a Strands Agent, or AWS/Bedrock access.

Phase 1.5 local acceptance was verified on 2026-11-02: the corpus list returns two papers (8 pages/21 chunks and 157 pages/157 chunks), all paper-inspection routes are present in Swagger, and the `E-CARGO` keyword query returns bounded source excerpts. Phase 2A added `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions; `sentence-transformers` 6.2.0) and a model-scoped local vector store. `pytest` has 18 passing tests and Ruff passes; PyMuPDF emits five upstream SWIG deprecation warnings.

The source PDFs remain local and ignored by Git. Persisted bibliographic fields are null until authorised metadata is supplied; the service does not infer titles, authors, dates, venues, DOI values, page labels, or research conclusions.

## Local commands

```bash
cd backend
set -a; source ../.env; set +a
export DATABASE_URL="postgresql+psycopg://enterprise_support:${POSTGRES_PASSWORD}@127.0.0.1:5432/enterprise_support"
.venv/bin/python -m pytest
.venv/bin/ruff check .

# Generate only missing local baseline embeddings; repeat runs skip existing rows.
.venv/bin/python -m app.embeddings.cli
```

After configuring ignored local `.env` from [.env.example](.env.example), start services with:

```bash
docker compose up --build -d
curl http://127.0.0.1:8000/health
```

Then open [Swagger UI](http://127.0.0.1:8000/docs). Under the **papers** group, use **Try it out** on:

- `GET /api/v1/papers` to see the two imported records and chunk counts.
- `GET /api/v1/papers/{document_id}` after copying an ID from the list.
- `GET /api/v1/papers/{document_id}/chunks` with `limit` and `offset` to inspect bounded source text.
- `GET /api/v1/papers/search` with `q=E-CARGO`; this is explicitly a bounded keyword search, not semantic retrieval.
- `GET /api/v1/papers/semantic-search` with `q=What is the E-CARGO model?` and optional `top_k` (1..20) or `document_id`. This is a pgvector cosine search over the local 384-dimensional model, not an answer or answer-confidence API.

For a negative-path check, use a non-existent `document_id` and expect `404`, or submit an empty `q` and expect `422`.

Ports bind only to `127.0.0.1`; the literature corpus mount is read-only. These endpoints have no authentication and are for local acceptance only. AWS/Bedrock needs explicit approval because calls may incur cost.

## Retrieval boundary

`/search` is lexical PostgreSQL `ILIKE` matching. `/semantic-search` embeds the query with the same local Sentence Transformers model used for corpus vectors and asks PostgreSQL/pgvector to rank one model family by cosine distance. Neither endpoint is an Agentic RAG answer service, and `similarity_score` is not a probability that a claim is correct.

The first local-model use downloads only public model artifacts from Hugging Face into the local cache. It does not send PDF or chunk text to Hugging Face. The current Compose configuration has no host-mounted model cache, so rebuilding the API container can require this download again. The local baseline has its own `chunk_embeddings` table, so it cannot mix its 384-dimensional vectors with the existing nullable Titan-reserved `paper_chunks.embedding vector(512)` column. Before an eventual Titan run, obtain explicit AWS cost/permission approval and keep model families separate.
