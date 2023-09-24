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

    try:
        if not os.path.exists(config_path): os.makedirs(config_path)
        shape_fn = os.path.join(config_path, 'window-shape')

        if os.path.exists(shape_fn):
            with open(shape_fn, 'r') as f:
                [x, y, width, height] = map(int, f.readlines())
    except:
        pass

    window = webview.create_window('Saturn', html = html, x = x, y = y, width = width, height = height)

    def save_shape():
        with atomic_write(shape_fn, mode='w', overwrite=True) as of:
            of.write(f'{int(window.x)}\n')
            of.write(f'{int(window.y)}\n')
            of.write(f'{int(window.width)}\n')
            of.write(f'{int(window.height)}\n')

    window.events.closing += save_shape

    webview.start()
