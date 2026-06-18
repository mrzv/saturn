import  os
import  webview
from    appdirs import AppDirs
from    atomicwrites import atomic_write

config_path = AppDirs('saturn', 'mrzv').user_config_dir

def view(html):
    x = None
    y = None
    width = 800
    height = 600
    shape_fn = None

    try:
        os.makedirs(config_path, exist_ok=True)
        shape_fn = os.path.join(config_path, 'window-shape')
    except Exception:
        pass

    try:
        if shape_fn is not None and os.path.exists(shape_fn):
            with open(shape_fn, 'r') as f:
                [x, y, width, height] = map(int, f.readlines())
    except (OSError, ValueError):
        pass

    window = webview.create_window('Saturn', html = html, x = x, y = y, width = width, height = height)

    def save_shape():
        if shape_fn is None:
            return

        try:
            with atomic_write(shape_fn, mode='w', overwrite=True) as of:
                of.write(f'{int(window.x)}\n')
                of.write(f'{int(window.y)}\n')
                of.write(f'{int(window.width)}\n')
                of.write(f'{int(window.height)}\n')
        except OSError:
            pass

    window.events.closing += save_shape

    webview.start()
