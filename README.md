# E-CARGO Knowledge Agent

An agentic RAG research assistant for E-CARGO and Role-Based Collaboration (RBC). The MVP answers research questions only from authorised academic literature, with validated citations and explicit abstention when evidence is insufficient.

## Scope

The intended corpus covers RBC, E-CARGO, GRA, GMRA, mathematical formulations, role-assignment algorithms, and documented applications including immigration policy simulation, clinical therapy planning, and scheduling. Sources must be user-provided, authorised, or publicly usable. This repository neither automatically downloads papers nor publishes restricted documents.

The MVP excludes GMRA solving, optimisation, experiment execution, arbitrary code execution, and automatic mathematical-model generation.

## Current status

Phase 1 currently has a local academic corpus: two user-provided PDFs, 178 extracted chunks, PostgreSQL 16 + pgvector, and Alembic migrations. The app provides read-only inspection APIs for that corpus and a PostgreSQL `ILIKE` keyword search. It does not provide embeddings, semantic retrieval, RAG answers, citations, an Agent, or AWS/Bedrock access.

The source PDFs remain local and ignored by Git. Persisted bibliographic fields are null until authorised metadata is supplied; the service does not infer titles, authors, dates, venues, DOI values, page labels, or research conclusions.

## Local commands

```bash
cd backend
.venv/bin/python -m pytest
.venv/bin/ruff check .
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

Ports bind only to `127.0.0.1`; the literature corpus mount is read-only. These endpoints have no authentication and are for local acceptance only. AWS/Bedrock needs explicit approval because calls may incur cost.
