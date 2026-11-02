# Phase 2A Retrieval Review — Initial Evidence Record

Run date: 2026-11-02. Corpus: two authorised local PDFs, queried through the fixed local model revision
`e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. Keyword uses PostgreSQL `ILIKE`; Semantic uses pgvector cosine.
Excerpts are shortened previews from the returned chunk, not a substitute for reading the source page.
For compact tables, `document_id / chunk_id` shows the document ID followed by its chunk suffix; concatenate
them with `-` to obtain the exact persisted `chunk_id` (for example,
`DOC-06b2c74db5a2ff9e0cc9-C0009-4f6da1f6722cea48`).

**Judgment boundary:** the labels below are automated preliminary observations based on returned text. They
record topical signals and failures to find an exact lexical phrase. They are **not** human relevance labels,
claim-level support judgments, Recall@K, MRR, or accuracy metrics.

## Q1. What is the E-CARGO model?

Expected topic: E-CARGO definition/components.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Keyword 1 | DOC-06b2c74db5a2ff9e0cc9 / C0000-95da7b6cd4dc305b | Computational Thinking.pdf / 1 | — | Computational Thinking, Object-Oriented Programming to Role-Based Collaboration… |
| Keyword 2 | DOC-06b2c74db5a2ff9e0cc9 / C0002-75c10cc94b5ccee9 | Computational Thinking.pdf / 2 | — | Compared to Human thinking, it is more logical, structured, and precise… |
| Keyword 3 | DOC-06b2c74db5a2ff9e0cc9 / C0003-f464cec1d8ea4931 | Computational Thinking.pdf / 2 | — | decomposition, pattern recognition, and modulization in OOP and E-CARGO modeling… |
| Keyword 4 | DOC-06b2c74db5a2ff9e0cc9 / C0007-3c0cf3dc045795ed | Computational Thinking.pdf / 3 | — | …sending and receiving messages, fulfilling their responsibilities… |
| Keyword 5 | DOC-06b2c74db5a2ff9e0cc9 / C0008-c87d14834cbc8de7 | Computational Thinking.pdf / 4 | — | RBC establishes a standardized collaboration process with explicitly defined entities… |
| Semantic 1 | DOC-06b2c74db5a2ff9e0cc9 / C0009-4f6da1f6722cea48 | Computational Thinking.pdf / 4 | 0.6606 | E-CARGO are abstracted as communication mechanisms between objects… |
| Semantic 2 | DOC-270eb5b15b6c2e09c5a7 / C0008-a493115f7235a1a4 | Thsis.pdf / 9 | 0.5850 | The E-CARGO based approach supports scalable and transparent decision making… |
| Semantic 3 | DOC-270eb5b15b6c2e09c5a7 / C0026-79b989508719dbdf | Thsis.pdf / 27 | 0.5763 | E-CARGO introduces the concept of an environment… |
| Semantic 4 | DOC-270eb5b15b6c2e09c5a7 / C0007-91e510f10eb6f383 | Thsis.pdf / 8 | 0.5087 | E-CARGO (Environments - Classes, Agents, Roles, Groups, and Objects)… |
| Semantic 5 | DOC-06b2c74db5a2ff9e0cc9 / C0011-c315e8e4f539e708 | Computational Thinking.pdf / 5 | 0.4644 | …specialization through subclassing, similar to inheritance in OOP… |

Automated preliminary: Semantic 1/3/4 have direct topic signals; human verification required for all rows.

## Q2. What is Role-Based Collaboration?

Expected topic: RBC definition and collaboration structure.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Keyword 1 | DOC-06b2c74db5a2ff9e0cc9 / C0000-95da7b6cd4dc305b | Computational Thinking.pdf / 1 | — | Computational Thinking, Object-Oriented Programming to Role-Based Collaboration… |
| Keyword 2 | DOC-06b2c74db5a2ff9e0cc9 / C0001-5cac6bae30395cec | Computational Thinking.pdf / 1 | — | This paper examines core principles and practical applications through… |
| Keyword 3 | DOC-06b2c74db5a2ff9e0cc9 / C0006-fad0ba6f51d353f3 | Computational Thinking.pdf / 3 | — | …supports stepwise refinement and modular development… |
| Keyword 4 | DOC-06b2c74db5a2ff9e0cc9 / C0019-c65dc2642bd32e70 | Computational Thinking.pdf / 7 | — | …reference text and bibliography entries… |
| Keyword 5 | DOC-06b2c74db5a2ff9e0cc9 / C0020-ebd269c9e325fbb6 | Computational Thinking.pdf / 7 | — | “Role-Based Collaboration and its Kernel Mechanisms”… |
| Semantic 1 | DOC-06b2c74db5a2ff9e0cc9 / C0010-18cd43d8e16518b0 | Computational Thinking.pdf / 4 | 0.7529 | roles define rights and responsibilities assigned to agents… |
| Semantic 2 | DOC-270eb5b15b6c2e09c5a7 / C0022-675318b32c041317 | Thsis.pdf / 23 | 0.6847 | RBC is defined as a computational methodology using roles… |
| Semantic 3 | DOC-270eb5b15b6c2e09c5a7 / C0024-c8e05842e8fc8116 | Thsis.pdf / 25 | 0.6671 | RBC defines a structured process for organizing collaboration… |
| Semantic 4 | DOC-06b2c74db5a2ff9e0cc9 / C0008-c87d14834cbc8de7 | Computational Thinking.pdf / 4 | 0.6287 | RBC establishes a standardized collaboration process… |
| Semantic 5 | DOC-270eb5b15b6c2e09c5a7 / C0026-79b989508719dbdf | Thsis.pdf / 27 | 0.6251 | E-CARGO introduces an environment for collaboration… |

Automated preliminary: semantic rows 1–4 show topical signals; Keyword 4 is likely bibliography/noise.

## Q3. How are roles assigned to agents?

Expected topic: agent qualification, GRA, and assignment. Exact keyword phrase: no result.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Semantic 1 | DOC-270eb5b15b6c2e09c5a7 / C0030-e98cc99a6dc50530 | Thsis.pdf / 31 | 0.7170 | Agent evaluation produces qualification evidence needed for assignment decisions; GRA… |
| Semantic 2 | DOC-06b2c74db5a2ff9e0cc9 / C0010-18cd43d8e16518b0 | Computational Thinking.pdf / 4 | 0.6733 | roles define rights and responsibilities assigned to agents… |
| Semantic 3 | DOC-270eb5b15b6c2e09c5a7 / C0010-9217fe4f63005d60 | Thsis.pdf / 11 | 0.6553 | roles rather than emerging solely from independent agent behavior… |
| Semantic 4 | DOC-270eb5b15b6c2e09c5a7 / C0023-15935c97eaa4b176 | Thsis.pdf / 24 | 0.5900 | RBC system components include roles, agents, groups, environments, objects… |
| Semantic 5 | DOC-270eb5b15b6c2e09c5a7 / C0039-ac53c46c64e5179e | Thsis.pdf / 40 | 0.5624 | framework provides methodological foundation for two case studies… |

Automated preliminary: Semantic 1/2 appear topical; no exact lexical phrase illustrates a Keyword limitation.

## Q4. What is an E-CARGO environment?

Expected topic: environment definition. Exact keyword phrase: no result.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Semantic 1 | DOC-270eb5b15b6c2e09c5a7 / C0026-79b989508719dbdf | Thsis.pdf / 27 | 0.7207 | environment defines the contextual space in which collaboration takes place… |
| Semantic 2 | DOC-06b2c74db5a2ff9e0cc9 / C0009-4f6da1f6722cea48 | Computational Thinking.pdf / 4 | 0.6977 | E-CARGO communication mechanisms between objects and Agents, Roles, Resources… |
| Semantic 3 | DOC-270eb5b15b6c2e09c5a7 / C0007-91e510f10eb6f383 | Thsis.pdf / 8 | 0.5018 | E-CARGO (Environments - Classes, Agents, Roles, Groups, and Objects)… |
| Semantic 4 | DOC-270eb5b15b6c2e09c5a7 / C0008-a493115f7235a1a4 | Thsis.pdf / 9 | 0.5012 | E-CARGO approach supports decision making… |
| Semantic 5 | DOC-270eb5b15b6c2e09c5a7 / C0090-39d09ffecfc15b19 | Thsis.pdf / 91 | 0.4811 | Unified Role-Based Abstraction under E-CARGO… |

Automated preliminary: Semantic 1 is a strong topic signal; other rows need review.

## Q5. What constraints does an environment specify?

Expected topic: environment/cardinality constraints. Exact keyword phrase: no result.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Semantic 1 | DOC-270eb5b15b6c2e09c5a7 / C0046-01b481ca0e17c9eb | Thsis.pdf / 47 | 0.5295 | framework should not be viewed merely as a technical allocation formulation… |
| Semantic 2 | DOC-270eb5b15b6c2e09c5a7 / C0041-b053db76cd906483 | Thsis.pdf / 42 | 0.5002 | components adjust suitability under contextual modifiers… |
| Semantic 3 | DOC-270eb5b15b6c2e09c5a7 / C0028-9a6242b45d65a9d3 | Thsis.pdf / 29 | 0.4949 | satisfy clinical indications, contraindications, and resource limitations… |
| Semantic 4 | DOC-270eb5b15b6c2e09c5a7 / C0026-79b989508719dbdf | Thsis.pdf / 27 | 0.4879 | environment specifies required roles and cardinality constraints… |
| Semantic 5 | DOC-270eb5b15b6c2e09c5a7 / C0100-c0c706dc4e6ccc8e | Thsis.pdf / 101 | 0.4863 | structural relationships rather than surface semantics… |

Automated preliminary: only Semantic 4 visibly names the expected constraint concept; all results require review.

## Q6. How does E-CARGO support decision making?

Expected topic: decision-making application.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Keyword 1 | DOC-270eb5b15b6c2e09c5a7 / C0003-ca20de5671bdc859 | Thsis.pdf / 4 | — | table-of-contents entry for E-CARGO policy scenario… |
| Keyword 2 | DOC-270eb5b15b6c2e09c5a7 / C0008-a493115f7235a1a4 | Thsis.pdf / 9 | — | E-CARGO based approach supports scalable and transparent decision making… |
| Keyword 3 | DOC-270eb5b15b6c2e09c5a7 / C0009-0d365fcb7737b4c5 | Thsis.pdf / 10 | — | complex coordination problems arise in social technical systems… |
| Keyword 4 | DOC-270eb5b15b6c2e09c5a7 / C0014-a6e0ca3340c5752e | Thsis.pdf / 15 | — | computational methods improve scalability… |
| Keyword 5 | DOC-270eb5b15b6c2e09c5a7 / C0025-21940d0fa93ad8d8 | Thsis.pdf / 26 | — | E-CARGO tuple component description… |
| Semantic 1 | DOC-270eb5b15b6c2e09c5a7 / C0008-a493115f7235a1a4 | Thsis.pdf / 9 | 0.7126 | E-CARGO based approach supports scalable and transparent decision making… |
| Semantic 2 | DOC-270eb5b15b6c2e09c5a7 / C0007-91e510f10eb6f383 | Thsis.pdf / 8 | 0.5699 | study explores E-CARGO/RBC as a framework… |
| Semantic 3 | DOC-06b2c74db5a2ff9e0cc9 / C0009-4f6da1f6722cea48 | Computational Thinking.pdf / 4 | 0.5666 | communication mechanisms between objects, Agents, Roles, Resources… |
| Semantic 4 | DOC-270eb5b15b6c2e09c5a7 / C0026-79b989508719dbdf | Thsis.pdf / 27 | 0.5579 | environment and collaboration context… |
| Semantic 5 | DOC-270eb5b15b6c2e09c5a7 / C0092-78e7babf39fb5ea5 | Thsis.pdf / 93 | 0.5117 | cross-case analysis highlights scalability and generality… |

Automated preliminary: Keyword/Semantic rank 1 contains the expected phrase; Keyword 1 is table-of-contents noise.

## Q7. How are groups formed in E-CARGO?

Expected topic: group formation. Exact keyword phrase: no result.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Semantic 1 | DOC-270eb5b15b6c2e09c5a7 / C0026-79b989508719dbdf | Thsis.pdf / 27 | 0.6479 | a group is formed when agents are assigned to roles within an environment… |
| Semantic 2 | DOC-06b2c74db5a2ff9e0cc9 / C0009-4f6da1f6722cea48 | Computational Thinking.pdf / 4 | 0.6296 | E-CARGO communication mechanisms… |
| Semantic 3 | DOC-270eb5b15b6c2e09c5a7 / C0012-bbc5206a1cc2531e | Thsis.pdf / 13 | 0.4993 | RBC provides a structured approach for organizing coordination… |
| Semantic 4 | DOC-06b2c74db5a2ff9e0cc9 / C0010-18cd43d8e16518b0 | Computational Thinking.pdf / 4 | 0.4912 | roles define rights and responsibilities assigned to agents… |
| Semantic 5 | DOC-270eb5b15b6c2e09c5a7 / C0007-91e510f10eb6f383 | Thsis.pdf / 8 | 0.4825 | E-CARGO component expansion… |

Automated preliminary: Semantic 1 visibly matches the topic; other rankings remain unreviewed.

## Q8. What roles do agents, resources, and objects play?

Expected topic: RBC entities. Exact keyword phrase: no result.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Semantic 1 | DOC-06b2c74db5a2ff9e0cc9 / C0010-18cd43d8e16518b0 | Computational Thinking.pdf / 4 | 0.7347 | roles define rights/responsibilities; agents act as role players… |
| Semantic 2 | DOC-270eb5b15b6c2e09c5a7 / C0023-15935c97eaa4b176 | Thsis.pdf / 24 | 0.6635 | core components include roles, agents, groups, environments, objects… |
| Semantic 3 | DOC-270eb5b15b6c2e09c5a7 / C0030-e98cc99a6dc50530 | Thsis.pdf / 31 | 0.6351 | agent evaluation and assignment decisions… |
| Semantic 4 | DOC-270eb5b15b6c2e09c5a7 / C0010-9217fe4f63005d60 | Thsis.pdf / 11 | 0.6177 | roles rather than independent agent behavior… |
| Semantic 5 | DOC-06b2c74db5a2ff9e0cc9 / C0008-c87d14834cbc8de7 | Computational Thinking.pdf / 4 | 0.5776 | RBC distinguishes objects and agents… |

Automated preliminary: Semantic 1/2/5 contain entity-topic signals; resource-specific support needs review.

## Q9. What is role assignment?

Expected topic: role-agent allocation and GRA.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Keyword 1 | DOC-06b2c74db5a2ff9e0cc9 / C0000-95da7b6cd4dc305b | Computational Thinking.pdf / 1 | — | title/abstract material… |
| Keyword 2 | DOC-06b2c74db5a2ff9e0cc9 / C0006-fad0ba6f51d353f3 | Computational Thinking.pdf / 3 | — | stepwise refinement and modular development… |
| Keyword 3 | DOC-06b2c74db5a2ff9e0cc9 / C0012-a4860711f86e143b | Computational Thinking.pdf / 5 | — | role-agent-object allocation and group as a partial solution… |
| Keyword 4 | DOC-06b2c74db5a2ff9e0cc9 / C0014-921274c7d8641f90 | Computational Thinking.pdf / 6 | — | classification supports prioritization during assignment process… |
| Keyword 5 | DOC-06b2c74db5a2ff9e0cc9 / C0015-ae9721f82df25e22 | Computational Thinking.pdf / 6 | — | role evaluation logic and scheduling framework… |
| Semantic 1 | DOC-06b2c74db5a2ff9e0cc9 / C0010-18cd43d8e16518b0 | Computational Thinking.pdf / 4 | 0.6493 | rights and responsibilities assigned to agents… |
| Semantic 2 | DOC-270eb5b15b6c2e09c5a7 / C0030-e98cc99a6dc50530 | Thsis.pdf / 31 | 0.6337 | GRA constructs a high-performing workable assignment… |
| Semantic 3 | DOC-270eb5b15b6c2e09c5a7 / C0047-16750c2220082df7 | Thsis.pdf / 48 | 0.6008 | accountability in policy and clinical treatment planning… |
| Semantic 4 | DOC-270eb5b15b6c2e09c5a7 / C0010-9217fe4f63005d60 | Thsis.pdf / 11 | 0.5579 | roles and individual decision variables… |
| Semantic 5 | DOC-270eb5b15b6c2e09c5a7 / C0023-15935c97eaa4b176 | Thsis.pdf / 24 | 0.5507 | RBC core components… |

Automated preliminary: Semantic 1/2 and Keyword 3–5 show topic signals; remaining rows need review.

## Q10. How does E-CARGO relate to object-oriented programming?

Expected topic: E-CARGO/OOP relationship.

| Retrieval | document_id / chunk_id | Source / page | Score | Excerpt preview |
| --- | --- | --- | ---: | --- |
| Keyword 1 | DOC-06b2c74db5a2ff9e0cc9 / C0000-95da7b6cd4dc305b | Computational Thinking.pdf / 1 | — | Computational Thinking, Object-Oriented Programming to Role-Based Collaboration… |
| Keyword 2 | DOC-06b2c74db5a2ff9e0cc9 / C0003-f464cec1d8ea4931 | Computational Thinking.pdf / 2 | — | OOP and E-CARGO modeling… |
| Keyword 3 | DOC-06b2c74db5a2ff9e0cc9 / C0019-c65dc2642bd32e70 | Computational Thinking.pdf / 7 | — | bibliography material… |
| Keyword 4 | DOC-270eb5b15b6c2e09c5a7 / C0101-c865a18abe5605df | Thsis.pdf / 102 | — | accomplished-paper bibliography entry… |
| Keyword 5 | DOC-270eb5b15b6c2e09c5a7 / C0106-f80341635bafdd23 | Thsis.pdf / 107 | — | bibliography entry… |
| Semantic 1 | DOC-06b2c74db5a2ff9e0cc9 / C0009-4f6da1f6722cea48 | Computational Thinking.pdf / 4 | 0.8140 | E-CARGO incorporates OOP principles such as Inheritance, Polymorphism, Encapsulation… |
| Semantic 2 | DOC-270eb5b15b6c2e09c5a7 / C0026-79b989508719dbdf | Thsis.pdf / 27 | 0.6500 | environment, required roles, cardinality constraints… |
| Semantic 3 | DOC-06b2c74db5a2ff9e0cc9 / C0011-c315e8e4f539e708 | Computational Thinking.pdf / 5 | 0.5634 | specialization through subclassing, similar to inheritance in OOP… |
| Semantic 4 | DOC-270eb5b15b6c2e09c5a7 / C0012-bbc5206a1cc2531e | Thsis.pdf / 13 | 0.5312 | RBC structured approach for multi-agent coordination… |
| Semantic 5 | DOC-06b2c74db5a2ff9e0cc9 / C0010-18cd43d8e16518b0 | Computational Thinking.pdf / 4 | 0.5023 | roles, agents, and collaboration components… |

Automated preliminary: Semantic 1/3 contain direct OOP-topic signals; Keyword 3–5 are likely bibliography noise.

## Review conclusion

The review records observable differences between exact lexical matching and semantic ranking, including
several questions for which no complete keyword phrase was found but semantic candidates contained topical
language. It does **not** establish that any answer is correct. A qualified reviewer must label relevant chunks
and claim support before retrieval-quality metrics or grounded-answer claims are published.
