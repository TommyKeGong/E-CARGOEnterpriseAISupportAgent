"""Provider boundary. No remote provider is called by the local default."""

from dataclasses import dataclass
from typing import Literal, Protocol

from app.rag.evidence import Evidence


class ProviderError(RuntimeError):
    """Controlled provider failure that is safe to expose as an API status."""


class ProviderTimeoutError(ProviderError):
    """Provider execution exceeded its configured deadline."""


@dataclass(frozen=True)
class CitationCandidate:
    document_id: str
    chunk_id: str
    pdf_page_number: int


@dataclass(frozen=True)
class ProviderOutput:
    answer: str
    citations: list[CitationCandidate]
    status: Literal["answered", "evidence_retrieved"] = "answered"


class LLMProvider(Protocol):
    provider_name: str

    def generate(self, question: str, evidence: list[Evidence]) -> ProviderOutput: ...


class MockLLMProvider:
    """Offline deterministic provider; it does not claim real LLM synthesis quality."""

    provider_name = "mock"

    def generate(self, question: str, evidence: list[Evidence]) -> ProviderOutput:
        if not evidence:
            raise ProviderError("mock provider requires selected evidence")
        citations = [
            CitationCandidate(
                document_id=item.document_id,
                chunk_id=item.chunk_id,
                pdf_page_number=item.pdf_page_number,
            )
            for item in evidence
        ]
        return ProviderOutput(
            answer=(
                "Mock provider (non-generative): selected local evidence for review; "
                "no scholarly synthesis or factual conclusion was generated."
            ),
            citations=citations,
            status="evidence_retrieved",
        )


def get_default_provider() -> LLMProvider:
    """Return the offline provider until an explicitly approved real provider is configured."""
    return MockLLMProvider()
