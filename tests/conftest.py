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
