from parser import Book, BookMetadata, ChapterContent
from parser import sanitize_chapter_html


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
