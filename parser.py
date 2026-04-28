from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, Comment

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
