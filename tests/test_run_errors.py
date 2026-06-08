import pytest
import sys

from saturn_notebook import __main__ as cli


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
