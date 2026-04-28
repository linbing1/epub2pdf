#!/usr/bin/env python3
"""epub2pdf — convert epub to kami-style reading PDF."""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

from language import detect
from parser import parse
from pdf import to_pdf
from renderer import render_html


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert epub to a reading PDF with kami visual style."
    )
    parser.add_argument("epub", help="Path to input .epub file")
    parser.add_argument("-o", "--output", help="Output PDF path (default: <book>.pdf)")
    parser.add_argument(
        "--size",
        choices=["a5", "6x9", "a4"],
        default="a5",
        help="Page size (default: a5)",
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="Keep intermediate HTML in <book>_build/ for debugging",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show WeasyPrint log messages",
    )
    args = parser.parse_args()

    epub_path = Path(args.epub)
    if not epub_path.exists():
        print(f"error: file not found: {epub_path}", file=sys.stderr)
        sys.exit(1)
    if not epub_path.suffix.lower() == ".epub":
        print(f"error: not an epub file: {epub_path}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.output:
        pdf_path = Path(args.output)
    else:
        pdf_path = epub_path.with_suffix(".pdf")

    if pdf_path.exists():
        print(f"overwriting {pdf_path}", file=sys.stderr)

    # Determine build directory
    if args.keep_html:
        build_dir = pdf_path.parent / (epub_path.stem + "_build")
        build_dir.mkdir(exist_ok=True)
        cleanup = False
    else:
        build_dir = Path(tempfile.mkdtemp(prefix="epub2pdf_"))
        cleanup = True

    t0 = time.time()

    try:
        print("parsing…", file=sys.stderr, end=" ", flush=True)
        images_dir = build_dir / "images"
        book = parse(str(epub_path), images_dir)
        n = len(book.chapters)
        print(f"→ {n} chapters", file=sys.stderr, end=" ", flush=True)

        lang = detect(book)

        print("→ rendering…", file=sys.stderr, end=" ", flush=True)
        html_path = render_html(book, lang, str(build_dir), size=args.size)

        print("→ PDF…", file=sys.stderr, end=" ", flush=True)
        to_pdf(html_path, pdf_path, book, verbose=args.verbose)

        elapsed = time.time() - t0
        print(f"→ done ({elapsed:.1f}s)", file=sys.stderr)
        print(f"{pdf_path}", file=sys.stdout)

    except Exception as e:
        print(f"\nerror: {e}", file=sys.stderr)
        if not cleanup:
            print(f"intermediate HTML preserved at: {build_dir}", file=sys.stderr)
        sys.exit(1)
    finally:
        if cleanup:
            shutil.rmtree(build_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
