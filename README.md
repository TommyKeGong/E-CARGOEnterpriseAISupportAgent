# E-CARGO Knowledge Agent

An agentic RAG research assistant for E-CARGO and Role-Based Collaboration (RBC). The MVP answers research questions only from authorised academic literature, with validated citations and explicit abstention when evidence is insufficient.

## Scope

The intended corpus covers RBC, E-CARGO, GRA, GMRA, mathematical formulations, role-assignment algorithms, and documented applications including immigration policy simulation, clinical therapy planning, and scheduling. Sources must be user-provided, authorised, or publicly usable. This repository neither automatically downloads papers nor publishes restricted documents.

The MVP excludes GMRA solving, optimisation, experiment execution, arbitrary code execution, and automatic mathematical-model generation.

## Current status

Phase 5A adds a local React/TypeScript/Vite/Tailwind interface with Chat, Library, and Sources views. It calls the existing FastAPI API with no fake research results, has a configurable Vite API base URL, and keeps the browser interface separate from the local/private backend boundary. The UI has passed static build and lint checks; it has not been exercised against a running database or Ollama service in this phase.

Phase 4C.1 real Ollama Agent verification remains incomplete: an interrupted attempt confirmed that the approved remote Ollama host listed `qwen3:4b`, but Docker infrastructure became unavailable before the four required end-to-end requests could be completed. Do not treat the JSON action protocol or Agent workflow as live-verified.

Phase 3B adds an optional Ollama provider. It remains disabled by default. Loopback Ollama endpoints work
without extra configuration; a private-network endpoint requires an explicit exact-match trust configuration
before the service sends selected, bounded evidence to it. The provider validates model citations against the
request-scoped evidence and PostgreSQL. Structural validation does not prove semantic entailment.

Phase 4A adds local/private document management: bounded PDF upload, existing pinned-model indexing, document
metadata/chunk inspection, and transactional deletion. The service does not retain uploaded PDF originals. These
unauthenticated management endpoints must not be exposed to the public internet.

Phase 4B adds a deterministic, route-independent research-tool foundation. It reuses persisted metadata,
chunks, and revision-scoped pgvector retrieval; it does not invoke an LLM or autonomously call tools.

Phase 4C adds a bounded local research-agent endpoint. It permits only the Phase 4B read-only tools, validates
every JSON action server-side, and applies backend limits before a configured Ollama model can receive another
tool result. It is not an unrestricted autonomous agent.

Phase 2A fixed the local model as `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` at revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` (384 dimensions; `sentence-transformers` 6.2.0). Phase 3A/3A.1 adds bounded evidence selection, structural citation validation, transparent local evidence inspection, and an offline Mock provider. Phase 3B adds local or explicitly trusted private-network Ollama inference. `pytest` has 54 passing tests and Ruff passes; PyMuPDF emits five upstream SWIG deprecation warnings.

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
- `POST /api/v1/ask` with `{ "question": "What is E-CARGO?", "top_k": 5, "debug_retrieval": true }`. With the current `mock` provider, it returns `status: "evidence_retrieved"` and `answer: null`, never a simulated scholarly answer. `evidence` contains the complete selected local chunk text, source, physical page, and retrieval `similarity_score`. Debug mode additionally returns every ranked Top-K candidate with `rank`, `selected`, and its actual `selection_reason`; it is for local inspection only.

To opt into Ollama, configure `RAG_PROVIDER=ollama`, `OLLAMA_MODEL`, and optionally `OLLAMA_BASE_URL` and
`OLLAMA_TIMEOUT_SECONDS`. No model name or endpoint is built into the application. For a non-loopback private
endpoint, `OLLAMA_TRUSTED_BASE_URL` must exactly equal `OLLAMA_BASE_URL`; this is an explicit acknowledgement
that selected evidence will be transmitted to that host. Do not configure an untrusted endpoint. An unavailable
service, timeout, missing model, or invalid model JSON becomes `provider_error`; an explicit empty-answer/
no-citation model abstention becomes `insufficient_evidence`.

```bash
RAG_PROVIDER=ollama
OLLAMA_MODEL=your-installed-model
OLLAMA_BASE_URL=http://your-approved-private-ollama-host:11434
OLLAMA_TRUSTED_BASE_URL=http://your-approved-private-ollama-host:11434
OLLAMA_TIMEOUT_SECONDS=120
```

## Local web interface (Phase 5A)

The frontend is a separate local development process. It does not start Docker, create a database, or configure
Ollama. Start the existing private backend first, then in a second terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

`VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`; set it in ignored `frontend/.env.local` when the local
backend uses another origin. The backend permits only explicit local origins from `FRONTEND_ORIGINS` (by default
`http://localhost:5173,http://127.0.0.1:5173`) and does not use wildcard CORS or browser credentials.

The Chat view calls `POST /api/v1/ask` or `POST /api/v1/agent/ask` according to the selected mode and renders
the returned evidence, citations, status, and safe agent trace. The Library view calls the existing document
list/upload/detail/chunk/delete endpoints. The Sources view calls the existing indexed page-context endpoint; it
labels that text as incomplete indexed extraction rather than an original PDF page. The frontend must remain
local/private until the API has authentication, authorisation, rights-aware content exposure, and a deployment
security review.

## Document management

`POST /api/v1/documents` accepts one `file` multipart field with an `application/pdf` PDF. It validates the
filename, type, PDF signature, parser result, and `DOCUMENT_UPLOAD_MAX_BYTES` (25 MiB by default), then uses the
same deterministic ingestion and pinned local embedding model as the command-line flow. A duplicate SHA-256 is
reported without regenerating embeddings. No upload path or temporary filename is returned.

```bash
curl --request POST http://127.0.0.1:8000/api/v1/documents \
  --form 'file=@/absolute/path/to/authorised-paper.pdf;type=application/pdf'

curl 'http://127.0.0.1:8000/api/v1/documents?limit=20&offset=0'
curl 'http://127.0.0.1:8000/api/v1/documents/DOC-example/chunks?pdf_page_number=4'
curl --request DELETE http://127.0.0.1:8000/api/v1/documents/DOC-example
```

Deletion removes exactly one document and its dependent embeddings/chunks/sections in a database transaction.
It cannot restore the source because upload originals are intentionally not retained. Do not expose upload or
delete endpoints beyond a local/private authenticated environment.

For a negative-path check, use a non-existent `document_id` and expect `404`, or submit an empty `q` and expect `422`.

Ports bind only to `127.0.0.1`; the literature corpus mount is read-only. These endpoints have no authentication and are for local acceptance only. AWS/Bedrock needs explicit approval because calls may incur cost.

## Research tools

`app.research_tools.ResearchTools` is the reusable, database-backed interface for future supervised agent work:

- `search_papers(query, top_k=5, document_ids=None)` returns at most 20 pgvector-ranked chunks with document,
  chunk, source filename, physical page, full indexed text, and similarity-score provenance.
- `list_papers(page=1, page_size=20)`, `get_document(document_id)`, and
  `read_chunks(document_id, page=1, page_size=20)` expose bounded persisted metadata and chunks.
- `get_page_context(document_id, pdf_page_number)` aggregates only persisted indexed chunks for one physical page.
  Its `is_complete_original_pdf_page` value is always `false`: an empty response can mean that the source page
  had no extractable/indexed text, and the API never recreates the original PDF page.

All tool results are Pydantic-validated and citation-compatible where they contain chunk provenance. Inputs are
bounded (`top_k` 1..20, `page_size` 1..100); unknown document IDs raise a typed not-found result in Python and
produce a 404 through the HTTP adapter. The only new HTTP capability is
`GET /api/v1/documents/{document_id}/pages/{pdf_page_number}/context`, because listing, detail, chunks, and
semantic search are already available through existing endpoints. Tools do not accept file paths, SQL, or shell
commands and remain local/private read-only functionality.

## Bounded research agent

`POST /api/v1/agent/ask` preserves the existing `/api/v1/ask` behaviour and adds a separate request-scoped
orchestrator. Its fixed registry is `search_papers`, `list_papers`, `get_document`, `read_chunks`, and
`get_page_context`; no filesystem, shell, SQL, network, write, or arbitrary tool is available. The defaults and
hard ceilings are five calls, eight steps, fifteen evidence items, 20,000 tool-result characters, and 180 seconds.
Optional environment settings beginning with `AGENT_` may only tighten those limits.

```bash
curl --request POST http://127.0.0.1:8000/api/v1/agent/ask \
  --header 'content-type: application/json' \
  --data '{"question":"Explain the E-CARGO role assignment mechanism.","max_tool_calls":5}'
```

With `RAG_PROVIDER=mock`, the endpoint retrieves auditable evidence but intentionally returns no generated
academic answer. With an explicitly trusted Ollama configuration, tool actions and final citations are strict JSON
and every citation is checked against evidence retrieved during the same request. That structural check does not
prove the answer is semantically supported. `debug_trace` contains only tool-event metadata, never prompts,
credentials, or provider payloads.

## Retrieval boundary

`/search` is lexical PostgreSQL `ILIKE` matching. `/semantic-search` embeds the query with the same local Sentence Transformers model used for corpus vectors and asks PostgreSQL/pgvector to rank one model family by cosine distance. Neither endpoint is an Agentic RAG answer service, and `similarity_score` is not a probability that a claim is correct.

The first local-model use downloads only public model artifacts from Hugging Face into the local cache. It does not send PDF or chunk text to Hugging Face. The current Compose configuration has no host-mounted model cache, so rebuilding the API container can require this download again. The local baseline has its own `chunk_embeddings` table, so it cannot mix its 384-dimensional vectors with the existing nullable Titan-reserved `paper_chunks.embedding vector(512)` column. Before an eventual Titan run, obtain explicit AWS cost/permission approval and keep model families separate.

## Grounded ask boundary

`POST /api/v1/ask` performs revision-scoped semantic retrieval, bounds/deduplicates selected evidence, and
structurally validates every provider citation against both the request's evidence and the PostgreSQL chunk/page
record. This prevents a provider from citing an un-retrieved or nonexistent chunk. It does not prove that an
answer's claim is semantically supported; that requires separate evaluation and human review.

The default `mock` provider intentionally produces no answer (`answer: null`). It makes no external request
and is only an end-to-end retrieval/evidence contract harness. The local `evidence.text` and debug fields expose
full authorised chunk text only for local development; production requires rights-aware access control and
content-exposure policy. A real Bedrock/Strands provider is future work requiring your
explicit permission, credentials, model/region selection, and cost review. See
[Phase 3A design](docs/phase3a_grounded_rag_design.md).
