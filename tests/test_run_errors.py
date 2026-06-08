import pytest

from saturn_notebook import __main__ as cli


def test_run_saves_then_reraises_notebook_exception(tmp_path):
    notebook = tmp_path / "error.py"
    output = tmp_path / "error.out.py"
    notebook.write_text("x = 1\nraise RuntimeError('boom')\ny = 2\n")

    with pytest.raises(RuntimeError, match="boom"):
        cli.run(str(notebook), str(output), no_mpi=True)

    assert output.exists()
    assert "raise RuntimeError('boom')" in output.read_text()
