import os

from saturn_notebook import utils


def test_composite_io_write_returns_written_length():
    out = utils.CompositeIO()

    assert out.write("hello") == 5


def test_composite_io_passthrough_writes_immediately():
    read_fd, write_fd = os.pipe()
    try:
        out = utils.CompositeIO()
        out.set_outfd(write_fd)

        out.write("streamed")

        assert os.read(read_fd, 8) == b"streamed"
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_collapse_carriage_return_ignores_extra_cursor_up():
    assert utils.collapse_carriage_return(["\x1b[A\x1b[Aoops\n"]) == ["oops\n"]
