import io

import pytest

from saturn_notebook import cells
from saturn_notebook.traceback import Traceback


def parse_text(text, **kwargs):
    return cells.parse(io.StringIO(text), '', **kwargs)


def test_parse_keeps_blank_lines_inside_code_cell():
    parsed = parse_text("x = 1\n\ny = 2\n")

    assert len(parsed) == 1
    assert isinstance(parsed[0], cells.CodeCell)
    assert parsed[0].code() == "x = 1\n\ny = 2"


def test_parse_splits_cells_on_markdown():
    parsed = parse_text("x = 1\n\n#m> text\n\ny = 2\n")

    types = [type(cell) for cell in parsed]

    assert types == [cells.CodeCell, cells.Blanks, cells.MarkdownCell, cells.Blanks, cells.CodeCell]


def test_empty_saturn_cell_is_safe_to_parse():
    parsed = parse_text("#saturn>")

    assert isinstance(parsed[0], cells.SaturnCell)
    assert parsed[0].external_fn == ''


def test_empty_variable_cell_is_safe_to_parse():
    parsed = parse_text("#var>")

    assert isinstance(parsed[0], cells.VariableCell)
    assert parsed[0].variables == ''
    assert parsed[0].expected_hash() is None


def test_parse_expands_top_level_main_guard_body_as_cells():
    parsed = parse_text(
        "if __name__ == '__main__':\n"
        "    print('main')\n"
        "    #m> heading\n"
        "    #chk>\n"
    )

    assert [type(cell) for cell in parsed] == [cells.CodeCell, cells.MarkdownCell, cells.CheckpointCell]
    assert parsed[0].code() == "print('main')"
    assert parsed[1].lines() == " heading\n"


def test_parse_main_guard_skips_else_branch():
    parsed = parse_text(
        "if __name__ == '__main__':\n"
        "    print('main')\n"
        "else:\n"
        "    print('imported')\n"
        "print('after')\n"
    )

    assert len(parsed) == 1
    assert isinstance(parsed[0], cells.CodeCell)
    assert parsed[0].code() == "print('main')\nprint('after')"


def test_external_zip_is_closed_after_parse(tmp_path, monkeypatch):
    external = tmp_path / "notebook.zip"
    external.touch()
    opened = []

    class FakeZip:
        def __init__(self, filename, mode):
            self.filename = filename
            self.mode = mode
            self.closed = False
            opened.append(self)

        def close(self):
            self.closed = True

    monkeypatch.setattr(cells.zipfile, "ZipFile", FakeZip)

    cells.parse(io.StringIO("x = 1\n"), str(external))

    assert len(opened) == 1
    assert opened[0].closed


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("notebook.py:10:2", ("notebook.py", 10, 2)),
        ("/tmp/path:with:colon/notebook.py:10:2", ("/tmp/path:with:colon/notebook.py", 10, 2)),
        ("plain-file.py", ("plain-file.py", -1, -1)),
        ("plain-file.py:not-int:2", ("plain-file.py:not-int:2", -1, -1)),
    ],
)
def test_traceback_filename_cell_parses_from_right(filename, expected):
    assert Traceback.filename_cell(filename) == expected
