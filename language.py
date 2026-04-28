from __future__ import annotations

from parser import Book

_CJK_RANGES = [
    (0x4E00, 0x9FFF),
    (0x3400, 0x4DBF),
    (0x20000, 0x2A6DF),
    (0xF900, 0xFAFF),
    (0x3000, 0x303F),
    (0xFF00, 0xFFEF),
]

_HIRAGANA_RANGE = (0x3040, 0x309F)
_KATAKANA_RANGE = (0x30A0, 0x30FF)


def _is_cjk(c: str) -> bool:
    cp = ord(c)
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)


def _is_kana(c: str) -> bool:
    cp = ord(c)
    return (
        _HIRAGANA_RANGE[0] <= cp <= _HIRAGANA_RANGE[1]
        or _KATAKANA_RANGE[0] <= cp <= _KATAKANA_RANGE[1]
    )


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

    all_text = " ".join(ch.content for ch in book.chapters)
    from bs4 import BeautifulSoup

    plain = BeautifulSoup(all_text, "html.parser").get_text()
    return _detect_from_text(plain)
