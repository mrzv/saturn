import  os
import  webview
from    appdirs import AppDirs
from    atomicwrites import atomic_write

config_path = AppDirs('saturn', 'mrzv').user_config_dir

def view(html):
    window = webview.create_window('Saturn', html = html)
    webview.start()
