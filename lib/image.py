import pixcat
import PIL

import matplotlib
matplotlib.use("module://lib.mpl")

import matplotlib.pyplot as plt
import io
import os

enabled = os.environ['TERM'] == 'xterm-kitty'      # TODO: find a better way

def is_mpl(result):        # determine if we can display this type
    return bool(plt.gcf().get_axes())

def save_mpl_png():
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    return buf.getvalue()

def show_png(buf):
    if enabled:
        im = PIL.Image.open(io.BytesIO(buf))
        pixcat.Image(im).show()
