"""PyMuPDF extraction with physical-page tracking and approximate word chunking."""

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pymupdf

TARGET_WORDS, OVERLAP_WORDS = 350, 50


class PDFIngestionError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedPage:
    pdf_page_index: int
    pdf_page_number: int
    text: str


@dataclass(frozen=True)
class PDFExtraction:
    source_path: Path
    content_hash: str
    page_count: int
    pages: tuple[ExtractedPage, ...]
    empty_text_pages: tuple[int, ...]
    replacement_character_pages: tuple[int, ...]


def clean_text(raw: str) -> str:
    return "\n".join(
        " ".join(line.split()) for line in raw.replace("\r", "\n").splitlines() if line.strip()
    )


def extract_pdf(path: Path) -> PDFExtraction:
    try:
        doc = pymupdf.open(path)
    except Exception as error:
        raise PDFIngestionError(f"Unable to open PDF {path.name}: {error}") from error
    try:
        if not doc.page_count:
            raise PDFIngestionError(f"PDF has no pages: {path.name}")
        pages, empty, replaced = [], [], []
        for index, page in enumerate(doc):
            raw = page.get_text("text")
            text, number = clean_text(raw), index + 1
            if not text:
                empty.append(number)
            if "\ufffd" in raw:
                replaced.append(number)
            pages.append(ExtractedPage(index, number, text))
    finally:
        doc.close()
    if not any(page.text for page in pages):
        raise PDFIngestionError(f"PDF has no extractable text: {path.name}")
    return PDFExtraction(
        path,
        sha256(path.read_bytes()).hexdigest(),
        len(pages),
        tuple(pages),
        tuple(empty),
        tuple(replaced),
    )


def chunk_extraction(
    extraction: PDFExtraction, target_words: int = TARGET_WORDS, overlap_words: int = OVERLAP_WORDS
) -> list[tuple[int, int, str]]:
    """Return page-bounded chunks. Word counts are deterministic token approximations."""
    if target_words <= overlap_words or overlap_words < 0:
        raise ValueError("Require target_words > overlap_words >= 0")
    chunks: list[tuple[int, int, str]] = []
    for page in extraction.pages:
        words, start = re.findall(r"\S+", page.text), 0
        while start < len(words):
            end = min(start + target_words, len(words))
            chunks.append((page.pdf_page_index, page.pdf_page_number, " ".join(words[start:end])))
            if end == len(words):
                break
            start = end - overlap_words
    return chunks
