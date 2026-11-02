"""Bounded, provenance-preserving evidence selection."""

from dataclasses import dataclass

from app.embeddings.local import SemanticResult


@dataclass(frozen=True)
class Evidence:
    document_id: str
    source_filename: str
    chunk_id: str
    pdf_page_number: int
    chunk_text: str
    similarity_score: float
    source_chunk_text: str | None = None

    @property
    def original_chunk_text(self) -> str:
        """Return the untruncated persisted chunk for transparency responses."""
        return self.source_chunk_text or self.chunk_text


@dataclass(frozen=True)
class EvidenceDecision:
    """Record a candidate's evidence-selection outcome without inferring factual support."""

    result: SemanticResult
    selected: bool
    selection_reason: str


@dataclass(frozen=True)
class EvidenceSelection:
    evidence: list[Evidence]
    decisions: list[EvidenceDecision]


class EvidenceSelector:
    """Keep diverse retrieved chunks without treating retrieval scores as answer confidence."""

    def __init__(
        self,
        *,
        max_evidence: int = 3,
        max_total_characters: int = 3_600,
        minimum_similarity: float = 0.45,
    ) -> None:
        self.max_evidence = max_evidence
        self.max_total_characters = max_total_characters
        self.minimum_similarity = minimum_similarity

    def evaluate(self, results: list[SemanticResult]) -> EvidenceSelection:
        selected: list[Evidence] = []
        decisions: list[EvidenceDecision] = []
        total_characters = 0
        seen_texts: set[str] = set()
        for result in results:
            if result.similarity_score < self.minimum_similarity:
                decisions.append(EvidenceDecision(result, False, "below_minimum_similarity"))
                continue
            normalized_text = " ".join(result.chunk_text.casefold().split())
            if normalized_text in seen_texts:
                decisions.append(EvidenceDecision(result, False, "duplicate_chunk_text"))
                continue
            remaining = self.max_total_characters - total_characters
            if remaining <= 0:
                decisions.append(
                    EvidenceDecision(result, False, "evidence_character_budget_exhausted")
                )
                continue
            if len(selected) >= self.max_evidence:
                decisions.append(EvidenceDecision(result, False, "max_evidence_reached"))
                continue
            chunk_text = result.chunk_text[:remaining]
            selected.append(
                Evidence(
                    document_id=result.document_id,
                    source_filename=result.source_filename,
                    chunk_id=result.chunk_id,
                    pdf_page_number=result.pdf_page_number,
                    chunk_text=chunk_text,
                    similarity_score=result.similarity_score,
                    source_chunk_text=result.chunk_text,
                )
            )
            decisions.append(EvidenceDecision(result, True, "selected"))
            seen_texts.add(normalized_text)
            total_characters += len(chunk_text)
        return EvidenceSelection(evidence=selected, decisions=decisions)

    def select(self, results: list[SemanticResult]) -> list[Evidence]:
        """Retain the established selection-only interface for non-debug callers."""
        return self.evaluate(results).evidence
