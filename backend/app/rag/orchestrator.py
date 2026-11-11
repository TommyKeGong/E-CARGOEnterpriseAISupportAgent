"""Orchestrate retrieval, bounded evidence, provider execution, and citation validation."""

from dataclasses import dataclass, field
from typing import Callable, Literal

from sqlalchemy.orm import Session

from app.embeddings.local import (
    COSINE_DISTANCE_METRIC,
    LOCAL_MODEL_ID,
    LOCAL_MODEL_REVISION,
    SemanticResult,
    semantic_search,
)
from app.rag.citations import CitationValidator, ValidCitation
from app.rag.evidence import Evidence, EvidenceDecision, EvidenceSelector
from app.rag.providers import LLMProvider

RAGStatus = Literal["answered", "evidence_retrieved", "insufficient_evidence", "provider_error"]


@dataclass(frozen=True)
class RetrievalMetadata:
    search_type: str
    model_id: str
    model_revision: str
    distance_metric: str
    retrieved_count: int
    selected_count: int


@dataclass(frozen=True)
class RAGResult:
    question: str
    answer: str | None
    status: RAGStatus
    provider: str
    citations: list[ValidCitation]
    retrieval: RetrievalMetadata
    invalid_citation_count: int = 0
    selected_evidence: list[Evidence] = field(default_factory=list)
    debug_retrieval: list[EvidenceDecision] = field(default_factory=list)


Retriever = Callable[..., list[SemanticResult]]


class GroundedRAGOrchestrator:
    def __init__(
        self,
        *,
        provider: LLMProvider,
        selector: EvidenceSelector | None = None,
        citation_validator: CitationValidator | None = None,
        retriever: Retriever = semantic_search,
    ) -> None:
        self.provider = provider
        self.selector = selector or EvidenceSelector()
        self.citation_validator = citation_validator or CitationValidator()
        self.retriever = retriever

    def answer(
        self,
        session: Session,
        question: str,
        encoder: object,
        *,
        top_k: int,
        debug_retrieval: bool = False,
    ) -> RAGResult:
        retrieved = self.retriever(session, question, encoder, top_k=top_k)
        selection = self.selector.evaluate(retrieved)
        evidence = selection.evidence
        debug_results = list(selection.decisions) if debug_retrieval else []
        metadata = RetrievalMetadata(
            search_type="semantic",
            model_id=LOCAL_MODEL_ID,
            model_revision=LOCAL_MODEL_REVISION,
            distance_metric=COSINE_DISTANCE_METRIC,
            retrieved_count=len(retrieved),
            selected_count=len(evidence),
        )
        if not evidence:
            return RAGResult(
                question=question,
                answer="Insufficient retrieved evidence supports an answer to this question.",
                status="insufficient_evidence",
                provider=self.provider.provider_name,
                citations=[],
                retrieval=metadata,
                debug_retrieval=debug_results,
            )
        try:
            output = self.provider.generate(question, evidence)
        except Exception:
            return RAGResult(
                question=question,
                answer="The configured provider could not produce an answer.",
                status="provider_error",
                provider=self.provider.provider_name,
                citations=[],
                retrieval=metadata,
                selected_evidence=evidence,
                debug_retrieval=debug_results,
            )
        if output.status == "insufficient_evidence":
            return RAGResult(
                question=question,
                answer="Insufficient retrieved evidence supports an answer to this question.",
                status="insufficient_evidence",
                provider=self.provider.provider_name,
                citations=[],
                retrieval=metadata,
                selected_evidence=evidence,
                debug_retrieval=debug_results,
            )
        validation = self.citation_validator.validate(session, evidence, output.citations)
        if validation.invalid_count or not validation.citations:
            return RAGResult(
                question=question,
                answer="The provider output was rejected because its citations did not validate.",
                status="insufficient_evidence",
                provider=self.provider.provider_name,
                citations=[],
                retrieval=metadata,
                invalid_citation_count=validation.invalid_count,
                selected_evidence=evidence,
                debug_retrieval=debug_results,
            )
        return RAGResult(
            question=question,
            answer=output.answer,
            status=output.status,
            provider=self.provider.provider_name,
            citations=validation.citations,
            retrieval=metadata,
            selected_evidence=evidence,
            debug_retrieval=debug_results,
        )
