import parser as parser_module
from parser import Book, BookMetadata, ChapterContent
from parser import TOCEntry, build_toc_map
from parser import sanitize_chapter_html
import tempfile
from pathlib import Path
from parser import parse


def test_imports():
    meta = BookMetadata(title="Test", language="zh", authors=["Author"])
    chapter = ChapterContent(id="c1", href="c1.xhtml", title="Chapter 1", content="<p>Body</p>", order=0)
    book = Book(metadata=meta, chapters=[chapter], images={}, source_path="test.epub")
    assert book.metadata.title == "Test"
    assert len(book.chapters) == 1
    assert book.chapters[0].title == "Chapter 1"


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


class _FakeItem:
    def __init__(self, item_type, name, content=b""):
        self._item_type = item_type
        self._name = name
        self._content = content

    def get_type(self):
        return self._item_type

    def get_name(self):
        return self._name

    def get_content(self):
        return self._content


class _FakeBook:
    def __init__(self, metadata, items, spine, toc=None):
        self._metadata = metadata
        self._items = items
        self.spine = spine
        self.toc = toc or []

    def get_metadata(self, namespace, key):
        return self._metadata.get((namespace, key), [])

    def get_items(self):
        return list(self._items.values())

    def get_item_with_id(self, item_id):
        return self._items.get(item_id)


def test_parse_keeps_image_only_chapter(monkeypatch, tmp_path):
    image_item = _FakeItem(parser_module.ebooklib.ITEM_IMAGE, "images/pic.jpg", b"image-bytes")
    chapter_item = _FakeItem(
        parser_module.ebooklib.ITEM_DOCUMENT,
        "chapter.xhtml",
        b'<html><body><img src="images/pic.jpg"/></body></html>',
    )
    fake_book = _FakeBook(
        metadata={("DC", "title"): [("Image Book", {})]},
        items={"img1": image_item, "chap1": chapter_item},
        spine=[("chap1", "yes")],
    )
    monkeypatch.setattr(parser_module.epub, "read_epub", lambda _path: fake_book)

    book = parse("fake.epub", tmp_path / "images")

    assert len(book.chapters) == 1
    assert '<img src="images/images_pic.jpg"' in book.chapters[0].content


def test_parse_image_names_avoid_collisions(monkeypatch, tmp_path):
    image_a = _FakeItem(parser_module.ebooklib.ITEM_IMAGE, "images/cover.jpg", b"a")
    image_b = _FakeItem(parser_module.ebooklib.ITEM_IMAGE, "assets/cover.jpg", b"b")
    fake_book = _FakeBook(
        metadata={},
        items={"img1": image_a, "img2": image_b},
        spine=[],
    )
    monkeypatch.setattr(parser_module.epub, "read_epub", lambda _path: fake_book)

    book = parse("fake.epub", tmp_path / "images")

    assert book.images["images/cover.jpg"] != book.images["assets/cover.jpg"]
    assert (tmp_path / book.images["images/cover.jpg"]).read_bytes() == b"a"
    assert (tmp_path / book.images["assets/cover.jpg"]).read_bytes() == b"b"
