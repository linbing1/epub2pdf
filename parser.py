from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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
