from pathlib import Path

import pymupdf
import pytest

from app.ingestion.pdf import PDFIngestionError, chunk_extraction, extract_pdf


def make_pdf(path: Path, pages: list[str]) -> None:
    document = pymupdf.open()
    for text in pages:
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_extract_pdf_tracks_physical_pages(tmp_path: Path) -> None:
    path = tmp_path / "paper.pdf"
    make_pdf(path, ["first page", "second page"])

    extraction = extract_pdf(path)

    assert extraction.page_count == 2
    assert [(page.pdf_page_index, page.pdf_page_number) for page in extraction.pages] == [
        (0, 1),
        (1, 2),
    ]


def test_chunking_is_page_bounded(tmp_path: Path) -> None:
    path = tmp_path / "paper.pdf"
    make_pdf(path, ["one two three four five six", "seven eight nine"])

    chunks = chunk_extraction(extract_pdf(path), target_words=4, overlap_words=1)

    assert [chunk[1] for chunk in chunks] == [1, 1, 2]
    assert chunks[1][2].split()[0] == "four"


def test_invalid_pdf_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid.pdf"
    path.write_text("not a PDF")

    with pytest.raises(PDFIngestionError, match="Unable to open PDF"):
        extract_pdf(path)
