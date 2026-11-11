# Phase 3A — Grounded RAG Design

## Scope and provider boundary

The implemented path is local and offline: semantic retrieval uses the pinned local embedding model, then an
explicitly labelled `mock` provider returns a non-generative evidence-review response. It does not claim LLM
answer quality and does not send corpus text to any third party.

A future provider implements the `LLMProvider` interface and receives only bounded selected evidence. A
Bedrock or Strands implementation is deliberately absent until the user approves credentials, model access,
region, and expected cost. An adapter may expose provider-specific timeouts and map failures to
`provider_error` without placing SDK code in API routes.

## Request flow

```text
POST /api/v1/ask
  -> query validation
  -> revision-scoped semantic retrieval (pgvector cosine)
  -> evidence selection (limit, exact duplicate removal, provenance retention)
  -> provider interface (Mock now; approved real provider later)
  -> structural citation validation (request evidence + PostgreSQL)
  -> evidence_retrieved (Mock) | answered (future real provider) | insufficient_evidence | provider_error
```

Retrieval score ranks chunks. In Phase 3A.1 it is returned with local evidence inspection, but is never
interpreted as answer confidence. Evidence selection's
minimum retrieval eligibility is an abstention control, not a factual-confidence estimate.

## Local evidence transparency

The offline Mock provider produces no answer: it returns `evidence_retrieved` with `answer: null` after
structural citation validation. The local API returns selected evidence using authoritative persisted chunk
text, source filename, physical PDF page, and pgvector score. `debug_retrieval=true` adds all requested Top-K
candidates in rank order with a factual selection reason. This enables review of threshold, exact-duplicate,
character-budget, and maximum-evidence exclusions without representing the result as LLM answer quality.

Full source text and debug data are local-development inspection features only. They are not written to logs
and require future rights-aware access control before public deployment.

## Citation validation

Each candidate citation carries document ID, chunk ID, and physical PDF page. Validation accepts it only if:

1. Its chunk was selected for this request.
2. Its document ID and page agree with the selected evidence record.
3. Its chunk exists in PostgreSQL and has the same document ID/page.

Invalid or hallucinated citations are rejected. This guarantees provenance structure only. Human review and
future groundedness evaluation are still required to determine whether the cited text supports the answer.

## Test and evaluation plan

Unit/integration tests cover evidence bounds/deduplication, no results, unsupported low-score retrieval,
provider timeout, provider failure, valid citations, hallucinated citations, and API request validation.

For a real provider, evaluate separately: retrieval relevance with human labels; citation precision and
recall; claim-level entailment/groundedness; abstention for unsupported questions; prompt-injection handling;
latency; and costs. Publish numerator, denominator, configuration, and failure cases rather than a single
unqualified accuracy figure.
