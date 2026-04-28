from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Optional
from urllib.parse import unquote

from bs4 import BeautifulSoup, Comment
import ebooklib
from ebooklib import epub

@dataclass
class ChapterContent:
    id: str
    href: str
    title: str
    content: str
    order: int


@dataclass
class BookMetadata:
    title: str
    language: str
    authors: list[str] = field(default_factory=list)
    publisher: Optional[str] = None


@dataclass
class Book:
    metadata: BookMetadata
    chapters: list[ChapterContent]
    images: dict[str, str]
    source_path: str


@dataclass
class TOCEntry:
    title: str
    href: str
    file_href: str
    anchor: str
    children: list["TOCEntry"] = field(default_factory=list)


def build_toc_map(toc: list[TOCEntry]) -> tuple[set[str], dict[str, str]]:
    """
    Recursively collect all TOC entries.
    Returns (valid_file_hrefs, file_href→title) where title is the first
    TOC entry that references each file.
    """
    valid_files: set[str] = set()
    title_map: dict[str, str] = {}

    def _walk(entries: list[TOCEntry]) -> None:
        for entry in entries:
            fh = entry.file_href
            if fh and fh not in title_map:
                valid_files.add(fh)
                title_map[fh] = entry.title
            elif fh:
                valid_files.add(fh)
            _walk(entry.children)

    _walk(toc)
    return valid_files, title_map


_KEEP_TAGS = {
    "p",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "em",
    "strong",
    "b",
    "i",
    "u",
    "s",
    "sup",
    "sub",
    "blockquote",
    "q",
    "br",
    "hr",
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    "table",
    "thead",
    "tbody",
    "tr",
    "td",
    "th",
    "img",
    "figure",
    "figcaption",
    "a",
}

_ATTR_WHITELIST: dict[str, set[str]] = {
    "a": {"href"},
    "img": {"src", "alt"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}


def sanitize_chapter_html(html: str) -> str:
    """Strip publisher styles/classes, unwrap unknown tags, downgrade h1->h2."""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "iframe", "form", "input", "button", "nav"]):
        tag.decompose()

    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    for h1 in soup.find_all("h1"):
        h1.name = "h2"

    for tag in soup.find_all(True):
        allowed_attrs = _ATTR_WHITELIST.get(tag.name, set())
        for attr in list(tag.attrs):
            if attr not in allowed_attrs:
                del tag.attrs[attr]

        if tag.name not in _KEEP_TAGS:
            tag.unwrap()

    return str(soup)


_FALLBACK_SKIP = re.compile(
    r"(nav|cover|title|copyright|colophon|toc)", re.IGNORECASE
)


def _parse_toc_recursive(toc_list: list) -> list[TOCEntry]:
    result = []
    for item in toc_list:
        if isinstance(item, tuple):
            section, children = item
            href = section.href or ""
            file_href = href.split("#")[0]
            anchor = href.split("#")[1] if "#" in href else ""
            entry = TOCEntry(
                title=section.title or "",
                href=href,
                file_href=file_href,
                anchor=anchor,
                children=_parse_toc_recursive(children),
            )
            result.append(entry)
        elif isinstance(item, epub.Link):
            href = item.href or ""
            file_href = href.split("#")[0]
            anchor = href.split("#")[1] if "#" in href else ""
            result.append(
                TOCEntry(
                    title=item.title or "",
                    href=href,
                    file_href=file_href,
                    anchor=anchor,
                )
            )
        elif isinstance(item, epub.Section):
            href = item.href or ""
            file_href = href.split("#")[0]
            anchor = href.split("#")[1] if "#" in href else ""
            result.append(
                TOCEntry(
                    title=item.title or "",
                    href=href,
                    file_href=file_href,
                    anchor=anchor,
                )
            )
    return result


def _extract_body(raw_html: str, image_map: dict[str, str]) -> str:
    """Extract <body> inner HTML, rewrite img srcs, sanitize."""
    soup = BeautifulSoup(raw_html, "html.parser")

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        src_decoded = unquote(src)
        basename = os.path.basename(src_decoded)
        if src_decoded in image_map:
            img["src"] = image_map[src_decoded]
        elif basename in image_map:
            img["src"] = image_map[basename]

    body = soup.find("body")
    inner = "".join(str(node) for node in body.contents) if body else str(soup)
    return sanitize_chapter_html(inner)


def parse(epub_path: str, images_dir: Path) -> Book:
    """
    Parse an epub file into a Book.
    Images are extracted to images_dir.
    Chapters are filtered and named via TOC reverse-lookup.
    """
    book_obj = epub.read_epub(epub_path)

    def _get_one(key: str) -> str:
        data = book_obj.get_metadata("DC", key)
        return data[0][0] if data else ""

    def _get_list(key: str) -> list[str]:
        data = book_obj.get_metadata("DC", key)
        return [value[0] for value in data] if data else []

    metadata = BookMetadata(
        title=_get_one("title") or "Untitled",
        language=_get_one("language") or "",
        authors=_get_list("creator"),
        publisher=_get_one("publisher") or None,
    )

    images_dir = Path(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)
    image_map: dict[str, str] = {}

    for item in book_obj.get_items():
        if item.get_type() == ebooklib.ITEM_IMAGE:
            raw_name = item.get_name()
            safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", os.path.basename(raw_name))
            local_path = images_dir / safe_name
            local_path.write_bytes(item.get_content())
            rel_path = f"images/{safe_name}"
            image_map[raw_name] = rel_path
            image_map[os.path.basename(raw_name)] = rel_path

    toc_entries = _parse_toc_recursive(book_obj.toc)
    valid_files, title_map = build_toc_map(toc_entries)
    use_toc = bool(valid_files)

    chapters: list[ChapterContent] = []
    order = 0

    for item_id, _linear in book_obj.spine:
        item = book_obj.get_item_with_id(item_id)
        if not item or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue

        href = item.get_name()
        basename = os.path.basename(href)

        if use_toc:
            if href not in valid_files and basename not in valid_files:
                continue
            title = title_map.get(href) or title_map.get(basename) or basename
        else:
            if _FALLBACK_SKIP.search(basename):
                continue
            raw = item.get_content().decode("utf-8", errors="ignore")
            soup_fb = BeautifulSoup(raw, "html.parser")
            header = soup_fb.find(["h1", "h2"])
            title = (
                header.get_text(strip=True)
                if header
                else basename.replace("_", " ").split(".")[0]
            )

        raw_html = item.get_content().decode("utf-8", errors="ignore")
        content = _extract_body(raw_html, image_map)

        text_content = BeautifulSoup(content, "html.parser").get_text(strip=True)
        if not text_content:
            import sys

            print(
                f"warning: chapter '{href}' is blank after sanitize, skipping",
                file=sys.stderr,
            )
            continue

        chapters.append(
            ChapterContent(
                id=item_id,
                href=href,
                title=title,
                content=content,
                order=order,
            )
        )
        order += 1

    return Book(
        metadata=metadata,
        chapters=chapters,
        images=image_map,
        source_path=epub_path,
    )
