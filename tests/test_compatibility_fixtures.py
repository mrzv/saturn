import io
import subprocess
import sys
from pathlib import Path

from saturn_notebook import cells


ROOT = Path(__file__).resolve().parents[1]
COMPAT = ROOT / "tests" / "compat"


def parse_fixture(name, **kwargs):
    with (COMPAT / name).open() as f:
        return cells.parse(f, "", **kwargs)


def test_legacy_inline_image_fixture_still_parses():
    parsed = parse_fixture("legacy-inline-image.py", show_only=True)

    output = next(cell for cell in parsed if isinstance(cell, cells.OutputCell))
    values = list(output.composite_)

    assert any(isinstance(value, io.StringIO) and "legacy image" in value.getvalue() for value in values)
    assert b"png-bytes" in values


def test_plain_python_main_guard_fixture_runs_as_python(tmp_path):
    source = COMPAT / "plain-python-main-guard.py"

    result = subprocess.run(
        [sys.executable, str(source)],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "42"
    assert (tmp_path / "main-guard-compat.marker").read_text() == "ran"


def test_plain_python_main_guard_fixture_expands_to_saturn_cells():
    parsed = parse_fixture("plain-python-main-guard.py")

    assert any(isinstance(cell, cells.MarkdownCell) for cell in parsed)
    assert any(isinstance(cell, cells.BreakCell) for cell in parsed)
    assert not any(
        isinstance(cell, cells.CodeCell) and "imported" in cell.code()
        for cell in parsed
    )
