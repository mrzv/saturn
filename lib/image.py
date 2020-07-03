import matplotlib
matplotlib.use("module://lib.mpl")

import matplotlib.pyplot as plt
import io
import os
import sys
from subprocess import run

enabled = os.environ['TERM'] == 'xterm-kitty' and sys.stdout.isatty()      # TODO: find a better way
seen = []

def is_new_mpl_available():
    global seen
    axes = plt.gcf().get_axes()
    for ax in axes:
        if ax not in seen:
            seen = axes
            return True
    seen = axes
    return False

def save_mpl_png():
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    return buf.getvalue()

def show_png(buf):
    if enabled:
        run(['kitty', '+kitten', 'icat'], input = buf)
