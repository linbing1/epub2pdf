from parser import Book, BookMetadata, ChapterContent


def test_imports():
    meta = BookMetadata(title="Test", language="zh", authors=["Author"])
    chapter = ChapterContent(id="c1", href="c1.xhtml", title="Chapter 1", content="<p>Body</p>", order=0)
    book = Book(metadata=meta, chapters=[chapter], images={}, source_path="test.epub")
    assert book.metadata.title == "Test"
    assert len(book.chapters) == 1
    assert book.chapters[0].title == "Chapter 1"
