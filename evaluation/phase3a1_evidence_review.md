# Phase 3A.1 — Retrieval Transparency Evidence Review

Run date: 2026-11-05. Corpus: two user-provided local PDFs (178 persisted chunks). This is an **automated
retrieval inspection**, not human relevance annotation or claim-support validation. Results were obtained from
the revision-pinned local 384-dimensional pgvector cosine search. `selected` reflects the current evidence
selector, not proof that the text supports a final answer. The API's local-development `evidence.text` and
`debug_retrieval[].text` fields return the complete persisted chunk; excerpts below are exact shortened
copies for review readability.

Selection policy for this run: retrieve `top_k=5` in descending similarity order; select candidates at or
above `0.45`, remove exact normalized-text duplicates, stop after three selected chunks or 3,600 characters.
The reported similarity score ranks retrieval results and is not answer confidence.

## Q1 — What is E-CARGO?

| Rank | Source/page | Chunk | Score | Selected/reason | Exact stored-text excerpt |
|---|---|---|---:|---|---|
| 1 | Computational Thinking.pdf p.4 | C0009 | 0.6753 | yes / selected | “E-CARGO are abstracted as communication mechanisms between objects, enabling dynamic interactions among Agents, Roles, and Resources...” |
| 2 | Thsis.pdf p.27 | C0026 | 0.5824 | yes / selected | “E-CARGO introduces the concept of an environment, which defines the contextual space in which collaboration takes place.” |
| 3 | Thsis.pdf p.9 | C0008 | 0.4284 | no / below_minimum_similarity | “The results show that the E-CARGO based approach supports scalable and transparent decision making.” |
| 4 | Thsis.pdf p.8 | C0007 | 0.4215 | no / below_minimum_similarity | “This study explores the application of the E-CARGO (Environments - Classes, Agents, Roles, Groups, and Objects) ...” |
| 5 | Computational Thinking.pdf p.5 | C0011 | 0.4141 | no / below_minimum_similarity | “The Divide and Conquer principle is one of the most important method applied in E-CARGO system...” |

Automated observation: topic-related evidence was selected, but a qualified reviewer should decide whether it
is sufficient for a concise definitional answer.

## Q2 — What is Role-Based Collaboration?

| Rank | Source/page | Chunk | Score | Selected/reason | Exact stored-text excerpt |
|---|---|---|---:|---|---|
| 1 | Computational Thinking.pdf p.4 | C0010 | 0.7529 | yes / selected | “roles define the rights and responsibilities assigned to agents, agents act as role players executing tasks...” |
| 2 | Thsis.pdf p.23 | C0022 | 0.6847 | yes / selected | “RBC is defined as a computational methodology that uses roles as the underlying mechanism to facilitate collaborative activities...” |
| 3 | Thsis.pdf p.25 | C0024 | 0.6671 | no / evidence_character_budget_exhausted | “RBC defines a structured process for organizing collaboration.” |
| 4 | Computational Thinking.pdf p.4 | C0008 | 0.6287 | no / evidence_character_budget_exhausted | “RBC establishes a standardized collaboration process with explicitly defined entities.” |
| 5 | Thsis.pdf p.27 | C0026 | 0.6251 | no / evidence_character_budget_exhausted | “An environment specifies required roles, their cardinality constraints, and the objects accessible to role players.” |

Automated observation: C0022 directly contains a definition-like statement; semantic entailment is still not
automatically verified.

## Q3 — What are the components of the E-CARGO model?

| Rank | Source/page | Chunk | Score | Selected/reason | Exact stored-text excerpt |
|---|---|---|---:|---|---|
| 1 | Computational Thinking.pdf p.4 | C0009 | 0.6877 | yes / selected | “dynamic interactions among Agents, Roles, and Resources...” |
| 2 | Thsis.pdf p.27 | C0026 | 0.6231 | yes / selected | “An environment specifies required roles, their cardinality constraints, and the objects accessible to role players.” |
| 3 | Thsis.pdf p.9 | C0008 | 0.6049 | no / evidence_character_budget_exhausted | “The E-CARGO framework provides...” |
| 4 | Thsis.pdf p.8 | C0007 | 0.5653 | no / evidence_character_budget_exhausted | “E-CARGO (Environments - Classes, Agents, Roles, Groups, and Objects) ...” |
| 5 | Computational Thinking.pdf p.5 | C0011 | 0.5105 | no / evidence_character_budget_exhausted | “Structural decomposition organizes problems into agent-, role-, and object-based groups...” |

Automated observation: the unselected abstract contains an explicit acronym expansion, while selected items are
topically relevant. The selector's bounded context can exclude a useful lower-ranked passage.

## Q4 — What is the difference between GRA and GMRA?

| Rank | Source/page | Chunk | Score | Selected/reason | Exact stored-text excerpt |
|---|---|---|---:|---|---|
| 1 | Thsis.pdf p.59 | C0058 | 0.4421 | no / below_minimum_similarity | “role assignments respect both suitability scores and capacity constraints while adhering to the GMRA framework.” |
| 2 | Thsis.pdf p.56 | C0055 | 0.4228 | no / below_minimum_similarity | “Unlike the GMRA problem, the NPRP requires optimizing the population allocation...” |
| 3 | Thsis.pdf p.36 | C0035 | 0.3976 | no / below_minimum_similarity | “The GMRA solution can thus be represented as a function call...” |
| 4 | Thsis.pdf p.37 | C0036 | 0.3906 | no / below_minimum_similarity | “The key difference lies in the agent side constraint that restrictions on single roles is replaced by a bounded multiple role constraint.” |
| 5 | Thsis.pdf p.35 | C0034 | 0.3742 | no / below_minimum_similarity | “Typical examples of GMRA arise in organizational management and service systems.” |

Automated observation: no evidence passed the current `0.45` eligibility threshold, so the API correctly
returns `insufficient_evidence`; C0036 merits human review as a potentially useful lower-scoring passage.

## Q5 — How are roles assigned to agents?

| Rank | Source/page | Chunk | Score | Selected/reason | Exact stored-text excerpt |
|---|---|---|---:|---|---|
| 1 | Thsis.pdf p.31 | C0030 | 0.7170 | yes / selected | “GRA constructs a high-performing workable group by assigning roles to agents...” |
| 2 | Computational Thinking.pdf p.4 | C0010 | 0.6733 | yes / selected | “roles define the rights and responsibilities assigned to agents...” |
| 3 | Thsis.pdf p.11 | C0010 | 0.6553 | yes / selected | “Shifting the modeling perspective from isolated entities to structured roles allows responsibilities and constraints...” |
| 4 | Thsis.pdf p.24 | C0023 | 0.5900 | no / evidence_character_budget_exhausted | “Agents act as role players and represent human users within the system.” |
| 5 | Thsis.pdf p.40 | C0039 | 0.5624 | no / evidence_character_budget_exhausted | “Agents represent decision participants within the system.” |

Automated observation: selected evidence is topic-related and contains an assignment statement; detailed
procedural claims still require human support review.

## Q6 — What is an E-CARGO environment?

| Rank | Source/page | Chunk | Score | Selected/reason | Exact stored-text excerpt |
|---|---|---|---:|---|---|
| 1 | Thsis.pdf p.27 | C0026 | 0.7207 | yes / selected | “an environment ... defines the contextual space in which collaboration takes place.” |
| 2 | Computational Thinking.pdf p.4 | C0009 | 0.6977 | yes / selected | “dynamic interactions among Agents, Roles, and Resources...” |
| 3 | Thsis.pdf p.8 | C0007 | 0.5018 | no / evidence_character_budget_exhausted | “E-CARGO (Environments - Classes, Agents, Roles, Groups, and Objects) ...” |
| 4 | Thsis.pdf p.9 | C0008 | 0.5012 | no / evidence_character_budget_exhausted | “The E-CARGO framework provides...” |
| 5 | Thsis.pdf p.91 | C0090 | 0.4811 | no / evidence_character_budget_exhausted | “the environment represents the immigration policy context...” |

Automated observation: C0026 is a directly relevant definitional passage; a human reviewer must judge final
claim coverage.

## Q7 — How does E-CARGO support computational thinking?

| Rank | Source/page | Chunk | Score | Selected/reason | Exact stored-text excerpt |
|---|---|---|---:|---|---|
| 1 | Thsis.pdf p.20 | C0019 | 0.7660 | yes / selected | “Computational Thinking ... emphasizes abstraction, decomposition, pattern recognition, and algorithmic reasoning...” |
| 2 | Thsis.pdf p.9 | C0008 | 0.6935 | yes / selected | “The E-CARGO framework provides...” |
| 3 | Computational Thinking.pdf p.2 | C0003 | 0.6578 | yes / selected | “decomposition, pattern recognition, and modulization in OOP and E-CARGO modeling.” |
| 4 | Computational Thinking.pdf p.4 | C0009 | 0.6188 | no / evidence_character_budget_exhausted | “E-CARGO incorporates core OOP principles such as Inheritance, Polymorphism, and Encapsulation...” |
| 5 | Thsis.pdf p.21 | C0020 | 0.5995 | no / evidence_character_budget_exhausted | “Computational Thinking ... reformulating seemingly difficult problems into solvable ones...” |

Automated observation: multiple passages are topically related, but the relationship wording should be
reviewed before a literature-grounded synthesis is stated.

## Q8 — What constraints are involved in role assignment?

| Rank | Source/page | Chunk | Score | Selected/reason | Exact stored-text excerpt |
|---|---|---|---:|---|---|
| 1 | Thsis.pdf p.48 | C0047 | 0.6631 | yes / selected | “the role assignment formulation produces a configuration of agents and roles that satisfies system-wide constraints...” |
| 2 | Thsis.pdf p.31 | C0030 | 0.6327 | yes / selected | “Agent evaluation produces the qualification evidence needed for assignment decisions...” |
| 3 | Thsis.pdf p.33 | C0032 | 0.6312 | yes / selected | “each role must be assigned exactly its required number of employees, resulting in a balanced and capacity-constrained allocation.” |
| 4 | Thsis.pdf p.37 | C0036 | 0.6300 | no / evidence_character_budget_exhausted | “single roles is replaced by a bounded multiple role constraint.” |
| 5 | Thsis.pdf p.46 | C0045 | 0.6174 | no / evidence_character_budget_exhausted | “binary decision constraints, role demand requirements, and agent capacity limitations.” |

Automated observation: the selected results discuss constraints, but C0045 contains a more explicit list and
was excluded only by the evidence character budget. This is an observable selector limitation, not a quality
metric.

## Cross-question observations and limitations

- No exact duplicate text occurred in these eight Top-5 sets. The current selector removes only exact
  whitespace/case-normalized duplicates; it does not remove near-duplicate or semantically overlapping chunks.
  That is intentional for now because an unvalidated overlap heuristic could suppress independently useful
  evidence.
- Candidates are evaluated strictly in pgvector rank order. They are selected only when their score meets
  `0.45`, before the maximum of three evidence chunks and 3,600-character budget is reached.
- Q4 demonstrates threshold sensitivity: a text that appears directly relevant on preliminary inspection can
  still be rejected. Q3 and Q8 demonstrate character-budget sensitivity: useful lower-ranked passages can be
  visible only in debug mode.
- None of these observations establishes Recall@K, MRR, precision, groundedness, or answer accuracy. Human
  relevance and claim-support labels remain required before reporting such metrics.
