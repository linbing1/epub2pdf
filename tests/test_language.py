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


def test_detect_ja_jp_normalizes_to_ja():
    assert detect(_make_book("ja-JP")) == "ja"


def test_detect_en_us_normalizes_to_en():
    assert detect(_make_book("en-US")) == "en"


def test_detect_zh_cn_normalizes_to_zh():
    assert detect(_make_book("zh-CN")) == "zh"


def test_detect_zh_tw_normalizes_to_zh():
    assert detect(_make_book("zh-TW")) == "zh"


def test_detect_fallback_cjk_chars():
    """No language metadata: >30% CJK -> zh."""
    text = "今天天气很好，我们去公园散步。" * 50
    assert detect(_make_book("", text)) == "zh"


def test_detect_fallback_hiragana():
    """Hiragana >5% -> ja."""
    text = "こんにちは世界。今日はいい天気ですね。" * 50
    assert detect(_make_book("", text)) == "ja"


def test_detect_fallback_latin_only():
    """No CJK, no kana -> en."""
    text = "The quick brown fox jumps over the lazy dog. " * 50
    assert detect(_make_book("", text)) == "en"


def test_detect_strips_html_before_fallback():
    text = '<div class="wrapper"><span>こんにちは世界。</span><script>ignored()</script></div>' * 50
    assert detect(_make_book("", text)) == "ja"


def test_detect_empty_defaults_zh():
    """Empty content, no metadata -> zh (tool's primary use case)."""
    assert detect(_make_book("", "")) == "zh"
