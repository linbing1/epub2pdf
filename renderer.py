from __future__ import annotations
import os
import shutil
from pathlib import Path
from html import escape

from parser import Book

_ASSETS_DIR = Path(__file__).parent / "assets"

_PAGE_SIZES = {
    "a5": ("148mm", "210mm"),
    "6x9": ("152.4mm", "228.6mm"),
    "a4": ("210mm", "297mm"),
}


def _cover_html(book: Book) -> str:
    title = escape(book.metadata.title)
    authors = escape(", ".join(book.metadata.authors)) if book.metadata.authors else ""
    author_line = f'<p class="author">{authors}</p>' if authors else ""
    return (
        '<section class="cover">'
        '<div class="cover-spacer"></div>'
        f"<h1>{title}</h1>"
        f"{author_line}"
        "</section>"
    )


def _toc_html(book: Book) -> str:
    items = []
    for i, ch in enumerate(book.chapters):
        title = escape(ch.title)
        items.append(
            f'<li><a href="#ch-{i}">'
            f'<span class="ch-title">{title}</span>'
            f'<span class="leader"></span>'
            f"</a></li>"
        )
    return (
        '<section class="toc">'
        "<h1>目录</h1>"
        f"<ol>{''.join(items)}</ol>"
        "</section>"
    )


def _chapters_html(book: Book) -> str:
    parts = []
    for i, ch in enumerate(book.chapters):
        title = escape(ch.title)
        parts.append(
            f'<section class="chapter" id="ch-{i}">'
            f"<h2>{title}</h2>"
            f"{ch.content}"
            "</section>"
        )
    return "".join(parts)


def render_html(book: Book, lang: str, out_dir: str, size: str = "a5") -> Path:
    """
    Write build.html, styles.css, and a fonts symlink into out_dir.
    Returns the path to build.html.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    shutil.copy(_ASSETS_DIR / "styles.css", out / "styles.css")

    fonts_link = out / "fonts"
    if not fonts_link.exists():
        fonts_src = _ASSETS_DIR / "fonts"
        if fonts_src.is_dir():
            os.symlink(fonts_src.resolve(), fonts_link)
        else:
            fonts_link.mkdir()

    w, h = _PAGE_SIZES.get(size, _PAGE_SIZES["a5"])
    page_size_style = f"<style>@page {{ size: {w} {h}; }}</style>"

    body = _cover_html(book) + _toc_html(book) + _chapters_html(book)

    html = (
        f"<!DOCTYPE html>\n"
        f'<html lang="{lang}">\n'
        f"<head>\n"
        f'<meta charset="utf-8"/>\n'
        f'<link rel="stylesheet" href="styles.css"/>\n'
        f"{page_size_style}\n"
        f"</head>\n"
        f"<body>\n{body}\n</body>\n"
        f"</html>"
    )

    html_path = out / "build.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path
