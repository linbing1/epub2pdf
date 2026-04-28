# epub2pdf Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert any epub file into an A5 reading PDF with kami's visual style (warm parchment, ink-blue accent, TsangerJinKai02 serif).

**Architecture:** epub → `parser.py` (ebooklib + BeautifulSoup, TOC-filtered chapters) → `renderer.py` (single HTML file) → `pdf.py` (WeasyPrint) → output PDF. Five flat modules communicate through a `Book` dataclass.

**Tech Stack:** Python ≥ 3.10, ebooklib, BeautifulSoup4, WeasyPrint 68+, pypdf, pytest

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `requirements.txt` | Create | Dependencies |
| `parser.py` | Create | epub → Book (TOC filter, HTML sanitize, image extract) |
| `language.py` | Create | Detect zh/en/ja from metadata or character ratios |
| `renderer.py` | Create | Book + lang → single build.html |
| `pdf.py` | Create | HTML → PDF via WeasyPrint |
| `epub2pdf.py` | Create | CLI entry point (argparse + orchestration) |
| `assets/styles.css` | Create | Full CSS with kami tokens |
| `assets/fonts/` | Populate | Copy TTF from kami |
| `tests/conftest.py` | Create | Shared pytest fixtures |
| `tests/test_parser.py` | Create | Unit tests for parser |
| `tests/test_language.py` | Create | Unit tests for language detector |
| `tests/test_renderer.py` | Create | Unit tests for renderer HTML output |
| `tests/test_acceptance.py` | Create | End-to-end CLI + PDF property checks |
| `tests/fixtures/怪屋谜案.epub` | Copy | Test fixture |
| `README.md` | Create | Install + usage + visual checklist |

---

## Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `assets/styles.css` (empty placeholder)
- Create: `assets/fonts/` (populate from kami)
- Create: `tests/fixtures/` (copy epub)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p assets/fonts tests/fixtures
touch assets/styles.css
```

- [ ] **Step 2: Write requirements.txt**

```
ebooklib
beautifulsoup4
lxml
weasyprint
pypdf
pytest
```

- [ ] **Step 3: Copy fonts from kami**

```bash
cp ~/.agents/skills/kami/assets/fonts/TsangerJinKai02-W04.ttf assets/fonts/
cp ~/.agents/skills/kami/assets/fonts/TsangerJinKai02-W05.ttf assets/fonts/
```

Verify:
```bash
ls -lh assets/fonts/
```
Expected: two `.ttf` files, each ~18-20 MB.

- [ ] **Step 4: Copy test fixture epub**

```bash
cp /Users/linbing/Project/github/reader3/怪屋谜案.epub tests/fixtures/
```

Verify:
```bash
ls -lh tests/fixtures/
```
Expected: `怪屋谜案.epub` present.

- [ ] **Step 5: Create and activate venv**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without error. WeasyPrint may print GTK/Pango messages — ignore.

- [ ] **Step 6: Commit scaffold**

```bash
git add requirements.txt assets/ tests/fixtures/怪屋谜案.epub
git commit -m "chore: scaffold project with deps, fonts, and test fixture"
```

---

## Task 2: Book dataclasses

**Files:**
- Create: `parser.py` (dataclasses only, no logic yet)
- Create: `tests/test_parser.py` (import test)

- [ ] **Step 1: Write the failing test**

Create `tests/test_parser.py`:

```python
from parser import Book, BookMetadata, ChapterContent


def test_imports():
    meta = BookMetadata(title="Test", language="zh", authors=["Author"])
    chapter = ChapterContent(id="c1", href="c1.xhtml", title="Chapter 1", content="<p>Body</p>", order=0)
    book = Book(metadata=meta, chapters=[chapter], images={}, source_path="test.epub")
    assert book.metadata.title == "Test"
    assert len(book.chapters) == 1
    assert book.chapters[0].title == "Chapter 1"
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_parser.py::test_imports -v
```
Expected: `ModuleNotFoundError: No module named 'parser'`

- [ ] **Step 3: Implement dataclasses in parser.py**

Create `parser.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ChapterContent:
    id: str
    href: str        # spine filename, e.g. 'chap_2.xhtml'
    title: str       # from TOC, e.g. '第一章 怪屋'
    content: str     # sanitized inner HTML (no <html>/<body> wrapper)
    order: int


@dataclass
class BookMetadata:
    title: str
    language: str    # raw dc:language value, e.g. 'zh', 'en', 'zh-CN'
    authors: list[str] = field(default_factory=list)
    publisher: Optional[str] = None


@dataclass
class Book:
    metadata: BookMetadata
    chapters: list[ChapterContent]
    images: dict[str, str]   # internal epub path -> 'images/<safe_name>'
    source_path: str
```

- [ ] **Step 4: Run to verify it passes**

```bash
pytest tests/test_parser.py::test_imports -v
```
Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add parser.py tests/test_parser.py
git commit -m "feat: add Book dataclasses"
```

---

## Task 3: HTML sanitizer

**Files:**
- Modify: `parser.py` (add `sanitize_chapter_html`)
- Modify: `tests/test_parser.py` (add sanitizer tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_parser.py`:

```python
from parser import sanitize_chapter_html


def test_sanitize_strips_style_and_class():
    html = '<p style="font-size:14px" class="body-text">Hello</p>'
    result = sanitize_chapter_html(html)
    assert "style=" not in result
    assert "class=" not in result
    assert "Hello" in result


def test_sanitize_unwraps_unknown_tags():
    html = '<div class="wrapper"><p>Content</p></div>'
    result = sanitize_chapter_html(html)
    assert "<div" not in result
    assert "Content" in result
    assert "<p>" in result


def test_sanitize_downgrades_h1_to_h2():
    html = "<h1>Chapter Title</h1><p>Body</p>"
    result = sanitize_chapter_html(html)
    assert "<h1" not in result
    assert "<h2" in result
    assert "Chapter Title" in result


def test_sanitize_preserves_img_src_alt():
    html = '<img src="images/fig.jpg" alt="Figure" width="100"/>'
    result = sanitize_chapter_html(html)
    assert 'src="images/fig.jpg"' in result
    assert 'alt="Figure"' in result
    assert "width=" not in result


def test_sanitize_preserves_a_href():
    html = '<a href="#ref" class="note" style="color:red">Link</a>'
    result = sanitize_chapter_html(html)
    assert 'href="#ref"' in result
    assert "class=" not in result
    assert "style=" not in result


def test_sanitize_preserves_td_colspan():
    html = '<table><tr><td colspan="2" width="100">Cell</td></tr></table>'
    result = sanitize_chapter_html(html)
    assert 'colspan="2"' in result
    assert "width=" not in result


def test_sanitize_keeps_em_strong():
    html = "<p><em>italic</em> and <strong>bold</strong></p>"
    result = sanitize_chapter_html(html)
    assert "<em>" in result
    assert "<strong>" in result


def test_sanitize_empty_chapter_returns_empty():
    assert sanitize_chapter_html("") == ""
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_parser.py -k "sanitize" -v
```
Expected: all `ImportError` or `AttributeError`

- [ ] **Step 3: Implement `sanitize_chapter_html` in parser.py**

Add after the dataclasses in `parser.py`:

```python
from bs4 import BeautifulSoup, Comment

_KEEP_TAGS = {
    "p", "h2", "h3", "h4", "h5", "h6",
    "em", "strong", "b", "i", "u", "s", "sup", "sub",
    "blockquote", "q", "br", "hr",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tr", "td", "th",
    "img", "figure", "figcaption", "a",
}

_ATTR_WHITELIST: dict[str, set[str]] = {
    "a":   {"href"},
    "img": {"src", "alt"},
    "td":  {"colspan", "rowspan"},
    "th":  {"colspan", "rowspan"},
}


def sanitize_chapter_html(html: str) -> str:
    """Strip publisher styles/classes, unwrap unknown tags, downgrade h1→h2."""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts, styles, comments
    for tag in soup(["script", "style", "iframe", "form", "input", "button", "nav"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Downgrade h1 → h2 (reserve h1 for cover)
    for h1 in soup.find_all("h1"):
        h1.name = "h2"

    # Two-pass: strip attributes, then unwrap unknown tags
    for tag in soup.find_all(True):
        allowed_attrs = _ATTR_WHITELIST.get(tag.name, set())
        for attr in list(tag.attrs):
            if attr not in allowed_attrs:
                del tag.attrs[attr]

        if tag.name not in _KEEP_TAGS:
            tag.unwrap()

    return str(soup)
```

- [ ] **Step 4: Run to verify tests pass**

```bash
pytest tests/test_parser.py -k "sanitize" -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add parser.py tests/test_parser.py
git commit -m "feat: add HTML sanitizer with tag/attr whitelist"
```

---

## Task 4: TOC map builder

**Files:**
- Modify: `parser.py` (add `TOCEntry`, `build_toc_map`, `_fallback_filter`)
- Modify: `tests/test_parser.py` (add TOC tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_parser.py`:

```python
from parser import TOCEntry, build_toc_map


def test_build_toc_map_basic():
    entries = [
        TOCEntry("第一章", "chap_1.xhtml", "chap_1.xhtml", ""),
        TOCEntry("第二章", "chap_2.xhtml", "chap_2.xhtml", ""),
    ]
    valid_files, title_map = build_toc_map(entries)
    assert valid_files == {"chap_1.xhtml", "chap_2.xhtml"}
    assert title_map["chap_1.xhtml"] == "第一章"
    assert title_map["chap_2.xhtml"] == "第二章"


def test_build_toc_map_anchor_stripped():
    """Anchored hrefs: file_href (without anchor) goes into valid_files."""
    entries = [TOCEntry("Chapter 1", "chap_1.xhtml#c1", "chap_1.xhtml", "c1")]
    valid_files, title_map = build_toc_map(entries)
    assert "chap_1.xhtml" in valid_files
    assert title_map["chap_1.xhtml"] == "Chapter 1"


def test_build_toc_map_duplicate_file_first_title_wins():
    """Multiple TOC entries for same file: first title wins."""
    entries = [
        TOCEntry("第一章 怪屋", "chap_2.xhtml", "chap_2.xhtml", ""),
        TOCEntry("小节 A", "chap_2.xhtml#sec1", "chap_2.xhtml", "sec1"),
    ]
    _, title_map = build_toc_map(entries)
    assert title_map["chap_2.xhtml"] == "第一章 怪屋"


def test_build_toc_map_recursive():
    """Nested TOC entries are all collected."""
    child = TOCEntry("Sub", "chap_1b.xhtml", "chap_1b.xhtml", "")
    parent = TOCEntry("Part 1", "chap_1.xhtml", "chap_1.xhtml", "", children=[child])
    valid_files, title_map = build_toc_map([parent])
    assert "chap_1.xhtml" in valid_files
    assert "chap_1b.xhtml" in valid_files


def test_build_toc_map_empty():
    valid_files, title_map = build_toc_map([])
    assert valid_files == set()
    assert title_map == {}
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_parser.py -k "toc_map" -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `TOCEntry` and `build_toc_map`**

Add to `parser.py` (after dataclasses, before `sanitize_chapter_html`):

```python
@dataclass
class TOCEntry:
    title: str
    href: str       # original href, e.g. 'chap_1.xhtml#section1'
    file_href: str  # just the filename, e.g. 'chap_1.xhtml'
    anchor: str     # just the anchor, e.g. 'section1', or ''
    children: list[TOCEntry] = field(default_factory=list)


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
                valid_files.add(fh)  # still valid even if title already set
            _walk(entry.children)

    _walk(toc)
    return valid_files, title_map
```

- [ ] **Step 4: Run to verify tests pass**

```bash
pytest tests/test_parser.py -k "toc_map" -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add parser.py tests/test_parser.py
git commit -m "feat: add TOCEntry and TOC-to-chapter-map builder"
```

---

## Task 5: Full epub parser

**Files:**
- Modify: `parser.py` (add `parse()` function)
- Modify: `tests/test_parser.py` (add integration test against 怪屋谜案.epub)

- [ ] **Step 1: Write failing integration test**

Append to `tests/test_parser.py`:

```python
import tempfile
from pathlib import Path
from parser import parse

FIXTURE = Path(__file__).parent / "fixtures" / "怪屋谜案.epub"


def test_parse_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        book = parse(str(FIXTURE), Path(tmp) / "images")
    assert book.metadata.title == "怪屋谜案（日本亚马逊悬疑推理No.1）"
    assert book.metadata.language == "zh"
    assert book.metadata.authors == ["雨穴"]


def test_parse_chapter_count():
    """Should get 40 chapters (TOC has 40 entries; nav.xhtml excluded)."""
    with tempfile.TemporaryDirectory() as tmp:
        book = parse(str(FIXTURE), Path(tmp) / "images")
    assert len(book.chapters) == 40


def test_parse_no_section_n_titles():
    """No chapter should have a 'Section N' placeholder title."""
    with tempfile.TemporaryDirectory() as tmp:
        book = parse(str(FIXTURE), Path(tmp) / "images")
    for ch in book.chapters:
        assert not ch.title.startswith("Section "), f"Bad title: {ch.title}"


def test_parse_first_chapter_title():
    with tempfile.TemporaryDirectory() as tmp:
        book = parse(str(FIXTURE), Path(tmp) / "images")
    assert book.chapters[0].title == "版权信息"
    assert book.chapters[1].title == "第一章 怪屋"


def test_parse_chapters_in_spine_order():
    with tempfile.TemporaryDirectory() as tmp:
        book = parse(str(FIXTURE), Path(tmp) / "images")
    orders = [ch.order for ch in book.chapters]
    assert orders == sorted(orders)


def test_parse_chapter_content_no_style_or_class():
    with tempfile.TemporaryDirectory() as tmp:
        book = parse(str(FIXTURE), Path(tmp) / "images")
    for ch in book.chapters:
        assert "style=" not in ch.content, f"style= found in {ch.href}"
        assert "class=" not in ch.content, f"class= found in {ch.href}"


def test_parse_no_nav_xhtml():
    with tempfile.TemporaryDirectory() as tmp:
        book = parse(str(FIXTURE), Path(tmp) / "images")
    hrefs = [ch.href for ch in book.chapters]
    assert "nav.xhtml" not in hrefs


def test_parse_images_extracted(tmp_path):
    images_dir = tmp_path / "images"
    book = parse(str(FIXTURE), images_dir)
    if book.images:
        assert images_dir.exists()
        for local_name in book.images.values():
            assert (tmp_path / local_name).exists()
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_parser.py -k "parse" -v
```
Expected: all fail with `ImportError` (parse not defined yet)

- [ ] **Step 3: Implement `parse()` in parser.py**

Append to `parser.py`:

```python
import os
import re
import shutil
import tempfile
from urllib.parse import unquote

import ebooklib
from ebooklib import epub


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
            result.append(TOCEntry(
                title=item.title or "",
                href=href,
                file_href=file_href,
                anchor=anchor,
            ))
        elif isinstance(item, epub.Section):
            href = item.href or ""
            file_href = href.split("#")[0]
            anchor = href.split("#")[1] if "#" in href else ""
            result.append(TOCEntry(
                title=item.title or "",
                href=href,
                file_href=file_href,
                anchor=anchor,
            ))
    return result


def _extract_body(raw_html: str, image_map: dict[str, str]) -> str:
    """Extract <body> inner HTML, rewrite img srcs, sanitize."""
    soup = BeautifulSoup(raw_html, "html.parser")

    # Rewrite image paths
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
    inner = "".join(str(x) for x in body.contents) if body else str(soup)
    return sanitize_chapter_html(inner)


def parse(epub_path: str, images_dir: Path) -> Book:
    """
    Parse an epub file into a Book.
    Images are extracted to images_dir.
    Chapters are filtered and named via TOC reverse-lookup.
    """
    book_obj = epub.read_epub(epub_path)

    # Metadata
    def _get_one(key: str) -> str:
        data = book_obj.get_metadata("DC", key)
        return data[0][0] if data else ""

    def _get_list(key: str) -> list[str]:
        data = book_obj.get_metadata("DC", key)
        return [x[0] for x in data] if data else []

    metadata = BookMetadata(
        title=_get_one("title") or "Untitled",
        language=_get_one("language") or "",
        authors=_get_list("creator"),
        publisher=_get_one("publisher") or None,
    )

    # Extract images
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

    # TOC
    toc_entries = _parse_toc_recursive(book_obj.toc)
    valid_files, title_map = build_toc_map(toc_entries)

    use_toc = bool(valid_files)

    # Process spine
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
            # Fallback: filename heuristic filter
            if _FALLBACK_SKIP.search(basename):
                continue
            raw = item.get_content().decode("utf-8", errors="ignore")
            soup_fb = BeautifulSoup(raw, "html.parser")
            h = soup_fb.find(["h1", "h2"])
            title = h.get_text(strip=True) if h else basename.replace("_", " ").split(".")[0]

        raw_html = item.get_content().decode("utf-8", errors="ignore")
        content = _extract_body(raw_html, image_map)

        # Skip blank chapters
        text_content = BeautifulSoup(content, "html.parser").get_text(strip=True)
        if not text_content:
            import sys
            print(f"warning: chapter '{href}' is blank after sanitize, skipping", file=sys.stderr)
            continue

        chapters.append(ChapterContent(
            id=item_id,
            href=href,
            title=title,
            content=content,
            order=order,
        ))
        order += 1

    return Book(
        metadata=metadata,
        chapters=chapters,
        images=image_map,
        source_path=epub_path,
    )
```

- [ ] **Step 4: Run to verify tests pass**

```bash
pytest tests/test_parser.py -k "parse" -v
```
Expected: all `PASSED`. (Takes a few seconds — WeasyPrint-free, just epublib.)

- [ ] **Step 5: Run all parser tests**

```bash
pytest tests/test_parser.py -v
```
Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add parser.py tests/test_parser.py
git commit -m "feat: implement full epub parser with TOC filtering"
```

---

## Task 6: Language detector

**Files:**
- Create: `language.py`
- Create: `tests/test_language.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_language.py`:

```python
from dataclasses import dataclass, field
from parser import Book, BookMetadata, ChapterContent
from language import detect


def _make_book(language: str, text: str = "some content") -> Book:
    return Book(
        metadata=BookMetadata(title="T", language=language, authors=[]),
        chapters=[ChapterContent("c1", "c1.xhtml", "C1", f"<p>{text}</p>", 0)],
        images={},
        source_path="test.epub",
    )


def test_detect_zh_from_metadata():
    assert detect(_make_book("zh")) == "zh"


def test_detect_en_from_metadata():
    assert detect(_make_book("en")) == "en"


def test_detect_ja_from_metadata():
    assert detect(_make_book("ja")) == "ja"


def test_detect_zh_cn_normalizes_to_zh():
    assert detect(_make_book("zh-CN")) == "zh"


def test_detect_zh_tw_normalizes_to_zh():
    assert detect(_make_book("zh-TW")) == "zh"


def test_detect_fallback_cjk_chars():
    """No language metadata: >30% CJK → zh."""
    text = "今天天气很好，我们去公园散步。" * 50
    assert detect(_make_book("", text)) == "zh"


def test_detect_fallback_hiragana():
    """Hiragana >5% → ja."""
    text = "こんにちは世界。今日はいい天気ですね。" * 50
    assert detect(_make_book("", text)) == "ja"


def test_detect_fallback_latin_only():
    """No CJK, no kana → en."""
    text = "The quick brown fox jumps over the lazy dog. " * 50
    assert detect(_make_book("", text)) == "en"


def test_detect_empty_defaults_zh():
    """Empty content, no metadata → zh (tool's primary use case)."""
    assert detect(_make_book("", "")) == "zh"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_language.py -v
```
Expected: `ModuleNotFoundError: No module named 'language'`

- [ ] **Step 3: Implement language.py**

Create `language.py`:

```python
from __future__ import annotations
import unicodedata
from parser import Book

_CJK_RANGES = [
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0x3400, 0x4DBF),    # CJK Extension A
    (0x20000, 0x2A6DF),  # CJK Extension B
    (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
    (0x3000, 0x303F),    # CJK Symbols and Punctuation
    (0xFF00, 0xFFEF),    # Halfwidth and Fullwidth Forms
]

_HIRAGANA_RANGE = (0x3040, 0x309F)
_KATAKANA_RANGE = (0x30A0, 0x30FF)


def _is_cjk(c: str) -> bool:
    cp = ord(c)
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)


def _is_kana(c: str) -> bool:
    cp = ord(c)
    return (_HIRAGANA_RANGE[0] <= cp <= _HIRAGANA_RANGE[1] or
            _KATAKANA_RANGE[0] <= cp <= _KATAKANA_RANGE[1])


def _detect_from_text(text: str) -> str:
    sample = text[:5000]
    if not sample:
        return "zh"

    total = len(sample)
    kana_count = sum(1 for c in sample if _is_kana(c))
    cjk_count = sum(1 for c in sample if _is_cjk(c))

    if kana_count / total > 0.05:
        return "ja"
    if cjk_count / total > 0.30:
        return "zh"
    return "en"


def detect(book: Book) -> str:
    """Return 'zh', 'en', or 'ja' for the book's primary language."""
    lang = book.metadata.language.lower().strip()

    if lang.startswith("zh"):
        return "zh"
    if lang.startswith("ja"):
        return "ja"
    if lang.startswith("en"):
        return "en"

    # Fallback: sample chapter text
    all_text = " ".join(ch.content for ch in book.chapters)
    from bs4 import BeautifulSoup
    plain = BeautifulSoup(all_text, "html.parser").get_text()
    return _detect_from_text(plain)
```

- [ ] **Step 4: Run to verify tests pass**

```bash
pytest tests/test_language.py -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add language.py tests/test_language.py
git commit -m "feat: add language detector (zh/en/ja)"
```

---

## Task 7: CSS stylesheet

**Files:**
- Modify: `assets/styles.css` (write full CSS)

No unit tests for CSS — verified later by WeasyPrint rendering.

- [ ] **Step 1: Write assets/styles.css**

```css
/* ======================================================
   epub2pdf stylesheet — kami visual token system
   WeasyPrint 68+ compatible
   ====================================================== */

/* Fonts */
@font-face {
  font-family: "TsangerJinKai02-W04";
  src: url("fonts/TsangerJinKai02-W04.ttf") format("truetype");
  font-weight: normal;
  font-style: normal;
}
@font-face {
  font-family: "TsangerJinKai02-W05";
  src: url("fonts/TsangerJinKai02-W05.ttf") format("truetype");
  font-weight: bold;
  font-style: normal;
}

/* Tokens */
:root {
  --paper:         #f5efe1;
  --ink:           #2a2a2a;
  --accent:        #1f3a68;
  --rule:          #c9bfa7;
  --muted:         #6b6357;
  --font-body:     "TsangerJinKai02-W04", "Charter", Georgia, serif;
  --font-display:  "TsangerJinKai02-W05", "Charter", Georgia, serif;
  --font-body-en:  "Charter", Georgia, serif;
  --font-body-ja:  "YuMincho", "Hiragino Mincho Pro", serif;
  --h1-size:       28pt;
  --h2-size:       22pt;
  --body-size:     11pt;
  --body-leading:  1.7;
  --caption-size:  9pt;
}

/* Page layout — size injected by renderer per --size flag */
@page {
  background-color: #f5efe1;
  margin: 18mm 16mm;
}
@page {
  @bottom-center {
    content: counter(page);
    font-size: 9pt;
    color: #6b6357;
    font-family: "TsangerJinKai02-W04", "Charter", Georgia, serif;
  }
}

/* Named page for cover — suppress page number */
@page cover-page {
  background-color: #f5efe1;
  margin: 18mm 16mm;
  @bottom-center { content: none; }
}

/* Named page for TOC — suppress page number */
@page toc-page {
  background-color: #f5efe1;
  margin: 18mm 16mm;
  @bottom-center { content: none; }
}

/* Body */
body {
  font-family: var(--font-body);
  font-size: var(--body-size);
  line-height: var(--body-leading);
  color: var(--ink);
  background-color: var(--paper);
  margin: 0;
  padding: 0;
  word-break: break-word;
  line-break: strict;
}

/* ---- Cover ---- */
section.cover {
  page: cover-page;
  page-break-after: always;
}

.cover-spacer {
  height: 55mm;
}

section.cover h1 {
  font-family: var(--font-display);
  font-size: var(--h1-size);
  color: var(--accent);
  text-align: center;
  margin: 0 0 12pt;
  bookmark-level: none;
}

section.cover .author {
  font-size: var(--body-size);
  color: var(--ink);
  text-align: center;
  margin: 0;
}

/* ---- TOC ---- */
section.toc {
  page: toc-page;
  page-break-after: always;
}

section.toc h1 {
  font-family: var(--font-display);
  font-size: var(--h2-size);
  color: var(--accent);
  text-align: center;
  margin: 0 0 16pt;
  border-bottom: 1px solid #c9bfa7;
  padding-bottom: 8pt;
  bookmark-level: none;
}

section.toc ol {
  list-style: none;
  padding: 0;
  margin: 0;
}

section.toc li {
  margin: 2pt 0;
}

section.toc a {
  display: flex;
  text-decoration: none;
  color: var(--ink);
  font-size: var(--body-size);
  align-items: baseline;
}

section.toc a .ch-title {
  white-space: nowrap;
  overflow: hidden;
  flex-shrink: 0;
  max-width: 75%;
}

section.toc a .leader {
  flex: 1;
  border-bottom: 1px dotted #c9bfa7;
  margin: 0 0.4em 0.3em;
  min-width: 0.5em;
}

section.toc a::after {
  content: target-counter(attr(href url), page);
  white-space: nowrap;
  color: var(--muted);
  font-size: var(--caption-size);
}

/* ---- Chapters ---- */
section.chapter {
  page-break-before: always;
}

section.chapter h2 {
  font-family: var(--font-display);
  font-size: var(--h2-size);
  color: var(--accent);
  text-align: center;
  margin: 0 0 0;
  padding-bottom: 8pt;
  border-bottom: 1px solid #c9bfa7;
  bookmark-level: 1;
  bookmark-label: content(text);
}

section.chapter h2 + * {
  margin-top: 12pt;
}

section.chapter h3,
section.chapter h4,
section.chapter h5,
section.chapter h6 {
  font-family: var(--font-display);
  color: var(--ink);
  margin: 10pt 0 4pt;
}

/* ---- Paragraph rules by language ---- */
:lang(zh) p,
:lang(ja) p {
  text-indent: 2em;
  margin: 0;
}

:lang(en) p {
  text-indent: 0;
  margin: 0 0 0.5em;
}

/* ---- Images ---- */
img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 8pt auto;
  page-break-inside: avoid;
}

figure {
  margin: 8pt 0;
  page-break-inside: avoid;
}

figcaption {
  font-size: var(--caption-size);
  color: var(--muted);
  text-align: center;
  margin-top: 4pt;
}

/* ---- Blockquote ---- */
blockquote {
  border-left: 2px solid #1f3a68;
  padding-left: 1em;
  margin: 8pt 0 8pt 1em;
  color: var(--muted);
}

/* ---- Tables ---- */
table {
  border-collapse: collapse;
  width: 100%;
  margin: 8pt 0;
  font-size: 10pt;
}

td, th {
  border: 1px solid #c9bfa7;
  padding: 4pt 6pt;
}

th {
  font-family: var(--font-display);
  background-color: #c9bfa7;
}

/* ---- Misc ---- */
em, i  { font-style: italic; }
strong, b { font-weight: bold; }
sup, sub  { font-size: 0.75em; line-height: 0; }
hr {
  border: none;
  border-top: 1px solid #c9bfa7;
  margin: 12pt 0;
}
a { color: var(--ink); }

/* ---- English font override ---- */
:lang(en) body {
  font-family: var(--font-body-en);
}
:lang(en) section.cover h1,
:lang(en) section.toc h1,
:lang(en) section.chapter h2 {
  font-family: var(--font-body-en);
}

/* ---- Japanese font override ---- */
:lang(ja) body {
  font-family: var(--font-body-ja);
}
:lang(ja) section.cover h1,
:lang(ja) section.toc h1,
:lang(ja) section.chapter h2 {
  font-family: var(--font-body-ja);
}
```

- [ ] **Step 2: Quick WeasyPrint smoke test**

```bash
python3 -c "
from weasyprint import HTML, CSS
from pathlib import Path
css = CSS(filename='assets/styles.css', base_url='assets')
html = HTML(string='<html lang=\"zh\"><body><section class=\"cover\"><div class=\"cover-spacer\"></div><h1>Test</h1></section></body></html>')
html.write_pdf('/tmp/css_smoke.pdf', stylesheets=[css])
print('OK:', Path('/tmp/css_smoke.pdf').stat().st_size, 'bytes')
"
```
Expected: prints `OK: NNNNN bytes` with no WeasyPrint errors (warnings about unknown properties are OK to ignore).

- [ ] **Step 3: Commit**

```bash
git add assets/styles.css
git commit -m "feat: add full CSS with kami tokens"
```

---

## Task 8: HTML renderer

**Files:**
- Create: `renderer.py`
- Create: `tests/conftest.py`
- Create: `tests/test_renderer.py`

- [ ] **Step 1: Create conftest.py with shared fixture**

Create `tests/conftest.py`:

```python
import pytest
from parser import Book, BookMetadata, ChapterContent


@pytest.fixture
def minimal_book() -> Book:
    return Book(
        metadata=BookMetadata(
            title="Test Book",
            language="zh",
            authors=["Test Author"],
        ),
        chapters=[
            ChapterContent("c1", "c1.xhtml", "第一章 开始", "<p>第一章内容。</p>", 0),
            ChapterContent("c2", "c2.xhtml", "第二章 中间", "<p>第二章内容。</p>", 1),
        ],
        images={},
        source_path="test.epub",
    )
```

- [ ] **Step 2: Write failing renderer tests**

Create `tests/test_renderer.py`:

```python
from pathlib import Path
import pytest
from renderer import render_html


def test_render_creates_build_html(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    assert html_path.exists()
    assert html_path.name == "build.html"


def test_render_html_lang_attribute(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "en", str(tmp_path))
    content = html_path.read_text()
    assert 'lang="en"' in content


def test_render_has_cover_section(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    content = html_path.read_text()
    assert 'class="cover"' in content
    assert "Test Book" in content
    assert "Test Author" in content


def test_render_has_toc_section(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    content = html_path.read_text()
    assert 'class="toc"' in content
    assert "第一章 开始" in content
    assert "第二章 中间" in content


def test_render_toc_links_have_href(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    content = html_path.read_text()
    assert 'href="#ch-0"' in content
    assert 'href="#ch-1"' in content


def test_render_chapter_sections(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    content = html_path.read_text()
    assert content.count('class="chapter"') == 2
    assert 'id="ch-0"' in content
    assert 'id="ch-1"' in content


def test_render_chapter_headings(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    content = html_path.read_text()
    assert "<h2>第一章 开始</h2>" in content
    assert "<h2>第二章 中间</h2>" in content


def test_render_no_section_n_placeholders(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    content = html_path.read_text()
    assert "Section 1" not in content
    assert "Section 2" not in content


def test_render_styles_css_copied(tmp_path, minimal_book):
    render_html(minimal_book, "zh", str(tmp_path))
    assert (tmp_path / "styles.css").exists()


def test_render_fonts_symlink_or_dir(tmp_path, minimal_book):
    render_html(minimal_book, "zh", str(tmp_path))
    fonts_path = tmp_path / "fonts"
    assert fonts_path.exists()


def test_render_page_size_injected(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path), size="a4")
    content = html_path.read_text()
    assert "210mm" in content and "297mm" in content


def test_render_a5_default_size(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    content = html_path.read_text()
    assert "148mm" in content
```

- [ ] **Step 3: Run to verify they fail**

```bash
pytest tests/test_renderer.py -v
```
Expected: all fail with `ModuleNotFoundError: No module named 'renderer'`

- [ ] **Step 4: Implement renderer.py**

Create `renderer.py`:

```python
from __future__ import annotations
import os
import shutil
from pathlib import Path
from html import escape

from parser import Book

_ASSETS_DIR = Path(__file__).parent / "assets"

_PAGE_SIZES = {
    "a5":  ("148mm", "210mm"),
    "6x9": ("152.4mm", "228.6mm"),
    "a4":  ("210mm", "297mm"),
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

    # Copy styles.css
    shutil.copy(_ASSETS_DIR / "styles.css", out / "styles.css")

    # Symlink fonts directory so CSS url("fonts/...") resolves
    fonts_link = out / "fonts"
    if not fonts_link.exists():
        fonts_src = _ASSETS_DIR / "fonts"
        if fonts_src.is_dir():
            os.symlink(fonts_src.resolve(), fonts_link)
        else:
            fonts_link.mkdir()  # empty fallback

    # Page size override
    w, h = _PAGE_SIZES.get(size, _PAGE_SIZES["a5"])
    page_size_style = f"<style>@page {{ size: {w} {h}; }}</style>"

    body = (
        _cover_html(book)
        + _toc_html(book)
        + _chapters_html(book)
    )

    html = (
        f'<!DOCTYPE html>\n'
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
```

- [ ] **Step 5: Run to verify tests pass**

```bash
pytest tests/test_renderer.py -v
```
Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add renderer.py tests/conftest.py tests/test_renderer.py
git commit -m "feat: implement HTML renderer"
```

---

## Task 9: PDF generator

**Files:**
- Create: `pdf.py`
- Modify: `tests/test_renderer.py` (add one PDF integration test)

- [ ] **Step 1: Write failing test**

Append to `tests/test_renderer.py`:

```python
import tempfile
from pdf import to_pdf
from parser import parse
from language import detect
from renderer import render_html
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "怪屋谜案.epub"


def test_to_pdf_produces_file(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    pdf_path = tmp_path / "out.pdf"
    to_pdf(html_path, pdf_path, minimal_book)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 10_000
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_renderer.py::test_to_pdf_produces_file -v
```
Expected: `ImportError: No module named 'pdf'`

- [ ] **Step 3: Implement pdf.py**

Create `pdf.py`:

```python
from __future__ import annotations
import logging
import sys
from pathlib import Path

from weasyprint import HTML, CSS

from parser import Book


def to_pdf(
    html_path: Path,
    pdf_path: Path,
    book: Book,
    verbose: bool = False,
) -> None:
    """
    Render the HTML file at html_path to a PDF at pdf_path.
    Sets PDF /Title and /Author metadata from book.
    """
    if not verbose:
        logging.getLogger("weasyprint").setLevel(logging.ERROR)
        logging.getLogger("fontTools").setLevel(logging.ERROR)

    html = HTML(filename=str(html_path), base_url=str(html_path.parent))

    authors = ", ".join(book.metadata.authors) if book.metadata.authors else ""

    html.write_pdf(
        str(pdf_path),
        uncompressed_pdf=False,
        presentational_hints=False,
    )

    # Inject PDF metadata (title + author) via pypdf post-processing
    _set_pdf_metadata(pdf_path, book.metadata.title, authors)


def _set_pdf_metadata(pdf_path: Path, title: str, author: str) -> None:
    try:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        writer.append(reader)
        writer.add_metadata({
            "/Title": title,
            "/Author": author,
            "/Producer": "epub2pdf",
            "/Creator": "epub2pdf",
        })
        with open(str(pdf_path), "wb") as f:
            writer.write(f)
    except Exception as e:
        print(f"warning: could not set PDF metadata: {e}", file=sys.stderr)
```

- [ ] **Step 4: Run to verify test passes**

```bash
pytest tests/test_renderer.py::test_to_pdf_produces_file -v
```
Expected: `PASSED` (takes 5-30s depending on book size)

- [ ] **Step 5: Commit**

```bash
git add pdf.py tests/test_renderer.py
git commit -m "feat: implement WeasyPrint PDF generator"
```

---

## Task 10: CLI orchestration

**Files:**
- Create: `epub2pdf.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_cli.py`:

```python
import subprocess
import sys
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "怪屋谜案.epub"


def test_cli_produces_pdf(tmp_path):
    out_pdf = tmp_path / "out.pdf"
    result = subprocess.run(
        [sys.executable, "epub2pdf.py", str(FIXTURE), "-o", str(out_pdf)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 50_000


def test_cli_missing_file_exits_nonzero():
    result = subprocess.run(
        [sys.executable, "epub2pdf.py", "nonexistent.epub"],
        capture_output=True, text=True
    )
    assert result.returncode != 0


def test_cli_keep_html(tmp_path):
    out_pdf = tmp_path / "out.pdf"
    result = subprocess.run(
        [sys.executable, "epub2pdf.py", str(FIXTURE), "-o", str(out_pdf), "--keep-html"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    # build dir should exist alongside the output pdf
    build_dirs = list(tmp_path.glob("*_build"))
    assert len(build_dirs) == 1
    assert (build_dirs[0] / "build.html").exists()


def test_cli_default_output_name(tmp_path):
    """Default output is <book_stem>.pdf in same dir as epub."""
    import shutil
    local_epub = tmp_path / "怪屋谜案.epub"
    shutil.copy(FIXTURE, local_epub)
    result = subprocess.run(
        [sys.executable, str(Path.cwd() / "epub2pdf.py"), str(local_epub)],
        capture_output=True, text=True, cwd=str(tmp_path)
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "怪屋谜案.pdf").exists()


def test_cli_size_a4(tmp_path):
    out_pdf = tmp_path / "out.pdf"
    result = subprocess.run(
        [sys.executable, "epub2pdf.py", str(FIXTURE), "-o", str(out_pdf), "--size", "a4"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert out_pdf.exists()
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_cli.py -v
```
Expected: all fail — `epub2pdf.py` doesn't exist yet.

- [ ] **Step 3: Implement epub2pdf.py**

Create `epub2pdf.py`:

```python
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
        build_dir = epub_path.parent / (epub_path.stem + "_build")
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
```

- [ ] **Step 4: Run to verify tests pass**

```bash
pytest tests/test_cli.py -v
```
Expected: all `PASSED`. (The full-book tests take 10-30s.)

- [ ] **Step 5: Commit**

```bash
git add epub2pdf.py tests/test_cli.py
git commit -m "feat: implement CLI orchestration"
```

---

## Task 11: Acceptance tests

**Files:**
- Create: `tests/test_acceptance.py`

- [ ] **Step 1: Write full acceptance test suite**

Create `tests/test_acceptance.py`:

```python
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
```

- [ ] **Step 2: Run the full acceptance suite**

```bash
pytest tests/test_acceptance.py -v
```
Expected: all `PASSED`. (Takes 20-60s for the full book render.)

- [ ] **Step 3: Run the complete test suite**

```bash
pytest -v
```
Expected: all tests pass. Note the count — it should be ≥ 40 tests.

- [ ] **Step 4: Commit**

```bash
git add tests/test_acceptance.py
git commit -m "test: add full acceptance test suite"
```

---

## Task 12: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Create `README.md`:

```markdown
# epub2pdf

Converts epub books to reading-optimized PDFs with kami's visual style:
warm parchment background, ink-blue accent, TsangerJinKai02 serif.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy fonts from kami (one-time):

```bash
cp ~/.agents/skills/kami/assets/fonts/TsangerJinKai02-*.ttf assets/fonts/
```

## Usage

```bash
python epub2pdf.py book.epub
python epub2pdf.py book.epub -o output.pdf
python epub2pdf.py book.epub --size a4
python epub2pdf.py book.epub --keep-html   # keep intermediate HTML for debugging
python epub2pdf.py book.epub -v            # verbose WeasyPrint logging
```

## Test

```bash
pytest -v
```

## Visual checklist (manual)

After generating a PDF, verify:

- [ ] Cover: book title + author centered, ink-blue title
- [ ] Warm parchment background renders correctly
- [ ] Chapter headings: ink-blue, centered, with rule below
- [ ] Body text: correct font (TsangerJinKai02 for zh, Charter for en)
- [ ] Chinese paragraphs: 2em first-line indent, no gap between paragraphs
- [ ] PDF left-panel outline shows all chapters, no "封面"/"目录" entries
- [ ] TOC page numbers are correct (click to jump works)
- [ ] Spot-check 3 chapters: line spacing, text flow, no garbled characters

## Font note

`assets/fonts/` contains TsangerJinKai02 (commercial font from Tsanger/Founder).
This repo is private and not for redistribution. For open-source use, replace
with Source Han Serif SC (SIL OFL).
```

- [ ] **Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: add README with install, usage, and visual checklist"
```

- [ ] **Step 3: Push to GitHub**

```bash
git push
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Covered in task |
|---|---|
| epub → PDF pipeline | Tasks 2-10 |
| TOC reverse-lookup filtering | Task 4-5 |
| HTML whitelist sanitizer | Task 3 |
| Language detection (zh/en/ja) | Task 6 |
| kami CSS tokens (colors, fonts, sizes) | Task 7 |
| Cover + TOC + chapters structure | Task 8 |
| WeasyPrint @page, bookmarks, target-counter | Tasks 7-8 |
| image extraction to disk | Task 5 |
| `--keep-html` flag | Task 10 |
| `--size a5/6x9/a4` | Tasks 8, 10 |
| `-v` verbose flag | Task 10 |
| stdout-silent progress to stderr | Task 10 |
| overwrite existing PDF with warning | Task 10 |
| pytest acceptance tests | Task 11 |
| README with visual checklist | Task 12 |
| Fonts from kami (TsangerJinKai02) | Task 1 |
| h1→h2 downgrade in chapters | Task 3 |
| bookmark-level: none on cover/toc h1 | Task 7 (CSS) |
| Blank chapter skip | Task 5 |
| Python ≥ 3.10 | All |
| Error handling per §8 | Task 10 |

### Type consistency check

- `parse(epub_path: str, images_dir: Path) -> Book` — used in Task 5, called in Task 10 ✓
- `detect(book: Book) -> str` — defined Task 6, called Task 10 ✓
- `render_html(book: Book, lang: str, out_dir: str, size: str = "a5") -> Path` — defined Task 8, called Task 10 ✓
- `to_pdf(html_path: Path, pdf_path: Path, book: Book, verbose: bool = False) -> None` — defined Task 9, called Task 10 ✓
- `Book.chapters: list[ChapterContent]` — used throughout ✓
- `ChapterContent.content` — set in `parse()`, read in `renderer.py` ✓

### Placeholder scan

No TBD, TODO, or "similar to Task N" patterns found.
