from saturn_notebook import image


def test_kitty_graphics_query_response_parser():
    assert image._kitty_graphics_query_succeeded(b'noise\033_Gi=31;OK\033\\') is True
    assert image._kitty_graphics_query_succeeded(b'\033_Gi=31;EINVAL\033\\') is False
    assert image._kitty_graphics_query_succeeded(b'\033_Gi=32;OK\033\\') is None
    assert image._kitty_graphics_query_succeeded(b'\033_Gi=31;OK') is None


def test_primary_device_attributes_response_parser():
    assert image._saw_primary_device_attributes(b'\033[?1;2c') is True
    assert image._saw_primary_device_attributes(b'\033[c') is True
    assert image._saw_primary_device_attributes(b'\033_Gi=31;OK\033\\') is False


def test_kitty_graphics_query_result_overrides_env(monkeypatch):
    monkeypatch.setattr(image, 'enabled', None)
    monkeypatch.setattr(image, '_output_isatty', lambda fd=None: True)
    monkeypatch.setattr(image, '_output_fd', lambda fd=None: 1)
    monkeypatch.setattr(image, '_query_kitty_graphics_protocol', lambda output_fd: False)
    monkeypatch.setenv('TERM', 'xterm-kitty')

    assert image._kitty_graphics_enabled() is False


def test_kitty_graphics_uses_env_when_query_is_unknown(monkeypatch):
    monkeypatch.setattr(image, 'enabled', None)
    monkeypatch.setattr(image, '_output_isatty', lambda fd=None: True)
    monkeypatch.setattr(image, '_output_fd', lambda fd=None: 1)
    monkeypatch.setattr(image, '_query_kitty_graphics_protocol', lambda output_fd: None)
    monkeypatch.setenv('TERM', 'xterm-kitty')

    assert image._kitty_graphics_enabled() is True


def test_non_tty_output_does_not_cache_detection(monkeypatch):
    monkeypatch.setattr(image, 'enabled', None)
    monkeypatch.setattr(image, '_output_isatty', lambda fd=None: False)

    assert image._kitty_graphics_enabled() is False
    assert image.enabled is None


def test_show_png_checks_requested_output_fd(monkeypatch):
    calls = []
    monkeypatch.setattr(image, '_kitty_graphics_enabled', lambda fd=None: calls.append(fd) or False)

    image.show_png(b'png', 42)

    assert calls == [42]
