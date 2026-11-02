# Phase 2A Local Retrieval Candidates

This is an evaluation **input**, not a published quality result. Each query below was checked with the
local keyword endpoint on 2026-11-02 and produced at least one result in the two imported PDFs. The `20`
counts mean the local inspection endpoint's result cap was reached; they are not corpus occurrence counts.

| Candidate query / concept | Bounded keyword results | Human relevance label needed |
| --- | ---: | --- |
| E-CARGO | 20 (capped) | Yes |
| Role-Based Collaboration | 16 | Yes |
| roles | 20 (capped) | Yes |
| agents | 20 (capped) | Yes |
| environment | 20 (capped) | Yes |
| decision making | 14 | Yes |
| assignment | 20 (capped) | Yes |
| group | 20 (capped) | Yes |
| object | 20 (capped) | Yes |
| collaboration | 20 (capped) | Yes |

For each query, a reviewer should annotate relevant `chunk_id` values and whether the physical PDF page
mapping is adequate for the intended claim. Only then may Recall@K, MRR, or other retrieval-quality metrics
be calculated. The candidate set makes no claim that every returned chunk semantically supports a research
answer.
