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
