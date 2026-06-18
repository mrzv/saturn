import importlib
import sys
import types


class ClosingEvent:
    def __init__(self):
        self.handler = None

    def __iadd__(self, handler):
        self.handler = handler
        return self


class FakeWindow:
    def __init__(self):
        self.x = 1
        self.y = 2
        self.width = 3
        self.height = 4
        self.events = types.SimpleNamespace(closing=ClosingEvent())


def import_viewer(monkeypatch, request):
    fake_window = FakeWindow()

    def start():
        fake_window.events.closing.handler()

    fake_webview = types.SimpleNamespace(
        create_window=lambda *args, **kwargs: fake_window,
        start=start,
    )
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    original_viewer = sys.modules.pop("saturn_notebook.viewer", None)

    def restore_viewer():
        sys.modules.pop("saturn_notebook.viewer", None)
        if original_viewer is not None:
            sys.modules["saturn_notebook.viewer"] = original_viewer

    request.addfinalizer(restore_viewer)
    return importlib.import_module("saturn_notebook.viewer")


def test_viewer_close_ignores_missing_config_path(monkeypatch, request):
    viewer = import_viewer(monkeypatch, request)

    def fail_makedirs(*args, **kwargs):
        raise OSError("config unavailable")

    def fail_atomic_write(*args, **kwargs):
        raise AssertionError("window shape should not be saved without a config path")

    monkeypatch.setattr(viewer.os, "makedirs", fail_makedirs)
    monkeypatch.setattr(viewer, "atomic_write", fail_atomic_write)

    viewer.view("<p>hello</p>")
