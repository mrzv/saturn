import pytest
import sys

from saturn_notebook import __main__ as cli
from saturn_notebook import cells, notebook


def test_run_saves_then_reraises_notebook_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pytest"])
    monkeypatch.setattr(sys, "path", list(sys.path))
    original_path = list(sys.path)
    notebook = tmp_path / "error.py"
    output = tmp_path / "error.out.py"
    notebook.write_text("x = 1\nraise RuntimeError('boom')\ny = 2\n")

    with pytest.raises(RuntimeError, match="boom"):
        cli.run(str(notebook), str(output), no_mpi=True)

    assert output.exists()
    assert "raise RuntimeError('boom')" in output.read_text()
    assert sys.argv == ["pytest"]
    assert sys.path == original_path


def test_run_restores_process_state_after_success(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pytest", "tests"])
    monkeypatch.setattr(sys, "path", list(sys.path))
    original_path = list(sys.path)
    notebook = tmp_path / "ok.py"
    output = tmp_path / "ok.out.py"
    notebook.write_text("import sys\nassert sys.argv[0].endswith('ok.py')\n")

    cli.run(str(notebook), str(output), no_mpi=True)

    assert output.exists()
    assert sys.argv == ["pytest", "tests"]
    assert sys.path == original_path


def test_run_saves_then_reraises_keyboard_interrupt(tmp_path):
    notebook = tmp_path / "interrupt.py"
    output = tmp_path / "interrupt.out.py"
    notebook.write_text("x = 1\nraise KeyboardInterrupt()\ny = 2\n")

    with pytest.raises(KeyboardInterrupt):
        cli.run(str(notebook), str(output), no_mpi=True)

    assert output.exists()
    assert "raise KeyboardInterrupt()" in output.read_text()
    assert "y = 2" in output.read_text()


def test_run_saves_then_reraises_system_exit(tmp_path):
    notebook = tmp_path / "exit.py"
    output = tmp_path / "exit.out.py"
    notebook.write_text("print('before exit')\nraise SystemExit(7)\nprint('after exit')\n")

    with pytest.raises(SystemExit) as exc_info:
        cli.run(str(notebook), str(output), no_mpi=True)

    assert exc_info.value.code == 7
    assert output.exists()
    assert "raise SystemExit(7)" in output.read_text()
    assert "print('after exit')" in output.read_text()


def test_forced_execution_records_traceback_and_continues():
    failing = cells.CodeCell()
    failing.append("raise RuntimeError('boom')\n")
    succeeding = cells.CodeCell()
    succeeding.append("result = 42\n")

    nb = notebook.Notebook(name="forced.py")
    nb.add([failing, succeeding])

    nb.process_all(lambda cell: None, force=True)

    output_cells = [cell for cell in nb.cells if isinstance(cell, cells.OutputCell)]
    assert any("RuntimeError" in item.getvalue() for cell in output_cells for item in cell.composite_ if hasattr(item, "getvalue"))
    assert nb.l["result"] == 42


def test_forced_execution_preserves_output_before_exception():
    failing = cells.CodeCell()
    failing.append("print('before boom')\nraise RuntimeError('boom')\n")

    nb = notebook.Notebook(name="forced.py")
    nb.add([failing])

    nb.process_all(lambda cell: None, force=True)

    output_cells = [cell for cell in nb.cells if isinstance(cell, cells.OutputCell)]
    rendered = "".join(
        item.getvalue()
        for cell in output_cells
        for item in cell.composite_
        if hasattr(item, "getvalue")
    )
    assert "before boom" in rendered
    assert "RuntimeError" in rendered


def test_auto_capture_runs_when_cell_result_is_none(monkeypatch):
    cell = cells.CodeCell()
    cell.append("x = 1\n")
    nb = notebook.Notebook(name="capture.py", auto_capture=True)
    nb.add([cell])

    monkeypatch.setattr(notebook.image, "is_new_mpl_available", lambda: True)
    monkeypatch.setattr(notebook.image, "save_mpl_png", lambda: b"png")

    nb.process_all(lambda cell: None, passthrough=False, output_spacing=False)

    output_cells = [cell for cell in nb.cells if isinstance(cell, cells.OutputCell)]
    assert any(item == b"png" for cell in output_cells for item in cell.composite_)


def test_traceback_falls_back_when_source_file_is_missing():
    failing = cells.CodeCell()
    failing.append("exec(compile(\"raise RuntimeError('boom')\", \"missing-source.py\", \"exec\"))\n")
    nb = notebook.Notebook(name="forced.py")
    nb.add([failing])

    nb.process_all(lambda cell: None, force=True)

    output_cells = [cell for cell in nb.cells if isinstance(cell, cells.OutputCell)]
    rendered = "".join(
        item.getvalue()
        for cell in output_cells
        for item in cell.composite_
        if hasattr(item, "getvalue")
    )
    assert "missing-source.py" in rendered
    assert "RuntimeError: boom" in rendered


def test_traceback_source_file_fallback_reraises_original_exception():
    failing = cells.CodeCell()
    failing.append("exec(compile(\"raise RuntimeError('boom')\", \"missing-source.py\", \"exec\"))\n")
    nb = notebook.Notebook(name="forced.py")
    nb.add([failing])

    with pytest.raises(RuntimeError, match="boom"):
        nb.process_all(lambda cell: None)


def test_traceback_falls_back_when_cell_id_is_invalid():
    failing = cells.CodeCell()
    failing.append("exec(compile(\"raise RuntimeError('boom')\", \"forced.py:999:1\", \"exec\"))\n")
    nb = notebook.Notebook(name="forced.py")
    nb.add([failing])

    nb.process_all(lambda cell: None, force=True)

    output_cells = [cell for cell in nb.cells if isinstance(cell, cells.OutputCell)]
    rendered = "".join(
        item.getvalue()
        for cell in output_cells
        for item in cell.composite_
        if hasattr(item, "getvalue")
    )
    assert "forced.py" in rendered
    assert "RuntimeError: boom" in rendered


def test_traceback_invalid_cell_id_fallback_reraises_original_exception():
    failing = cells.CodeCell()
    failing.append("exec(compile(\"raise RuntimeError('boom')\", \"forced.py:999:1\", \"exec\"))\n")
    nb = notebook.Notebook(name="forced.py")
    nb.add([failing])

    with pytest.raises(RuntimeError, match="boom"):
        nb.process_all(lambda cell: None)
