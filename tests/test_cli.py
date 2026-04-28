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
