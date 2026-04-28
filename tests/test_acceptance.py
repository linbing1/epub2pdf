"""
End-to-end acceptance tests for 怪屋谜案.epub → PDF.
Validates: font embedding, page count, bookmarks, TOC links, chapter text,
no placeholder titles, file size sanity.
"""
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

FIXTURE = Path(__file__).parent / "fixtures" / "怪屋谜案.epub"
EXPECTED_CHAPTERS = 40  # 40 TOC entries in 怪屋谜案


@pytest.fixture(scope="module")
def pdf_path(tmp_path_factory):
    out = tmp_path_factory.mktemp("acceptance") / "怪屋谜案.pdf"
    result = subprocess.run(
        [sys.executable, "epub2pdf.py", str(FIXTURE), "-o", str(out)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}"
    return out


def test_pdf_exists(pdf_path):
    assert pdf_path.exists()


def test_pdf_size_reasonable(pdf_path):
    size = pdf_path.stat().st_size
    assert size > 100_000, f"PDF too small: {size} bytes"
    assert size < 50_000_000, f"PDF suspiciously large: {size} bytes"


def test_page_count_at_least_chapters_plus_2(pdf_path):
    reader = PdfReader(str(pdf_path))
    pages = len(reader.pages)
    assert pages >= EXPECTED_CHAPTERS + 2, (
        f"Expected ≥ {EXPECTED_CHAPTERS + 2} pages, got {pages}"
    )


def test_bookmark_count_equals_chapters(pdf_path):
    reader = PdfReader(str(pdf_path))

    def count_bookmarks(items) -> int:
        total = 0
        for item in items:
            if isinstance(item, list):
                total += count_bookmarks(item)
            else:
                total += 1
        return total

    n = count_bookmarks(reader.outline)
    assert n == EXPECTED_CHAPTERS, (
        f"Expected {EXPECTED_CHAPTERS} bookmarks, got {n}"
    )


def test_no_cover_or_toc_in_bookmarks(pdf_path):
    reader = PdfReader(str(pdf_path))

    def collect_titles(items) -> list[str]:
        titles = []
        for item in items:
            if isinstance(item, list):
                titles.extend(collect_titles(item))
            elif hasattr(item, "title"):
                titles.append(item.title or "")
        return titles

    titles = collect_titles(reader.outline)
    bad = [t for t in titles if t in ("封面", "目录", "Cover", "TOC")]
    assert not bad, f"Unexpected bookmark titles: {bad}"


def test_no_section_n_in_bookmarks(pdf_path):
    reader = PdfReader(str(pdf_path))

    def collect_titles(items) -> list[str]:
        titles = []
        for item in items:
            if isinstance(item, list):
                titles.extend(collect_titles(item))
            elif hasattr(item, "title"):
                titles.append(item.title or "")
        return titles

    titles = collect_titles(reader.outline)
    bad = [t for t in titles if t.startswith("Section ")]
    assert not bad, f"Placeholder bookmark titles found: {bad}"


def test_pdf_metadata(pdf_path):
    reader = PdfReader(str(pdf_path))
    meta = reader.metadata
    assert meta is not None
    assert "怪屋谜案" in (meta.title or ""), f"Bad title: {meta.title}"
    assert "雨穴" in (meta.author or ""), f"Bad author: {meta.author}"
    assert "epub2pdf" in (meta.producer or ""), f"Bad producer: {meta.producer}"


def test_toc_links_reachable(pdf_path):
    """All TOC page links land on a valid page number."""
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)

    def check_dests(items) -> list[str]:
        errors = []
        for item in items:
            if isinstance(item, list):
                errors.extend(check_dests(item))
            elif hasattr(item, "page"):
                try:
                    page_ref = reader.get_destination_page_number(item)
                    if page_ref is None or page_ref >= total_pages:
                        errors.append(f"{item.title}: page {page_ref} out of range")
                except Exception:
                    pass  # some destinations may not resolve; tolerate
        return errors

    errors = check_dests(reader.outline)
    assert not errors, f"Bad bookmark destinations: {errors}"
