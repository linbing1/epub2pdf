from pathlib import Path
import pytest
import tempfile
from pdf import to_pdf
from parser import parse
from language import detect
from renderer import render_html

FIXTURE = Path(__file__).parent / "fixtures" / "怪屋谜案.epub"


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


def test_to_pdf_produces_file(tmp_path, minimal_book):
    html_path = render_html(minimal_book, "zh", str(tmp_path))
    pdf_path = tmp_path / "out.pdf"
    to_pdf(html_path, pdf_path, minimal_book)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 10_000
