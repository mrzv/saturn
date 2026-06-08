from typing import Any, Optional


class State:
    def __init__(self, *, root: bool = True, using: bool = False, comm: Optional[Any] = None) -> None:
        self.root = root
        self.using = using
        self.comm = comm


def detect(no_mpi: bool = False) -> State:
    if no_mpi:
        return State()

    try:
        from mpi4py import MPI
    except Exception:
        return State()

    comm = MPI.COMM_WORLD
    return State(root=comm.Get_rank() == 0, using=comm.Get_size() > 1, comm=comm)
