import sys
import types

from saturn_notebook import cells, notebook
from saturn_notebook import mpi


def test_detect_no_mpi_returns_single_process_state():
    state = mpi.detect(no_mpi=True)

    assert state.root is True
    assert state.using is False
    assert state.comm is None


def test_detect_uses_mpi_rank_and_size(monkeypatch):
    class Comm:
        def Get_rank(self):
            return 1

        def Get_size(self):
            return 4

    fake_mpi4py = types.ModuleType("mpi4py")
    fake_mpi4py.MPI = types.SimpleNamespace(COMM_WORLD=Comm())
    monkeypatch.setitem(sys.modules, "mpi4py", fake_mpi4py)

    state = mpi.detect()

    assert state.root is False
    assert state.using is True
    assert state.comm is fake_mpi4py.MPI.COMM_WORLD


def test_process_all_can_disable_live_passthrough(capsys):
    cell = cells.CodeCell()
    cell.append("print('hidden live output')\n")
    nb = notebook.Notebook(name="mpi.py")
    nb.add([cell])

    nb.process_all(lambda cell: None, passthrough=False, output_spacing=False)

    captured = capsys.readouterr()
    assert captured.out == ""
    output_cells = [cell for cell in nb.cells if isinstance(cell, cells.OutputCell)]
    assert any("hidden live output" in item.getvalue() for cell in output_cells for item in cell.composite_ if hasattr(item, "getvalue"))
