import matplotlib
matplotlib.use("module://saturn_notebook.mpl")

import matplotlib.pyplot as plt
import io
import os
import sys
from base64 import standard_b64encode
from . import utils
from more_itertools import peekable

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

def show_png(buf, fd = None):
    if enabled:
        icat(buf, fd)

def icat(buf, fd = None):
    def serialize_gr_command(cmd, payload=None):
       cmd = ','.join('{}={}'.format(k, v) for k, v in cmd.items())
       ans = io.BytesIO()
       w = ans.write
       w(b'\033_G'), w(cmd.encode('ascii'))
       if payload:
          w(b';')
          w(payload)
       w(b'\033\\')
       return ans.getbuffer()

    if fd is None:
        write = sys.stdout.buffer.write
    else:
        write = lambda x: os.write(fd, x)

    pchunk = peekable(utils.chunkstring(standard_b64encode(buf), 4096))
    cmd = { 'a': 'T', 'f': 100 }
    for chunk in pchunk:
        cmd['m'] = 1 if pchunk else 0
        write(serialize_gr_command(cmd, chunk))
        cmd.clear()
    write(b'\n')
