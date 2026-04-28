from __future__ import annotations

import logging
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from weasyprint import CSS, HTML

from parser import Book


def _set_pdf_metadata(pdf_path: Path, title: str, authors: list[str]) -> None:
    try:
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        writer.append(reader)
        writer.add_metadata(
            {
                "/Title": title,
                "/Author": ", ".join(authors),
                "/Producer": "WeasyPrint",
                "/Creator": "epub2pdf",
            }
        )
        with pdf_path.open("wb") as fh:
            writer.write(fh)
    except Exception as exc:  # pragma: no cover - best-effort metadata update
        print(f"warning: failed to set PDF metadata for {pdf_path}: {exc}", file=sys.stderr)


def to_pdf(html_path: Path, pdf_path: Path, book: Book, verbose: bool = False) -> None:
    if not verbose:
        logging.getLogger("weasyprint").setLevel(logging.ERROR)
        logging.getLogger("fontTools").setLevel(logging.ERROR)

    html = HTML(filename=str(html_path), base_url=str(html_path.parent))
    html.write_pdf(
        str(pdf_path),
        uncompressed_pdf=False,
        presentational_hints=False,
    )

    _set_pdf_metadata(pdf_path, book.metadata.title, book.metadata.authors)
