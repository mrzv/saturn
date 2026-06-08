import sys
import types

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
