import matplotlib
matplotlib.use("module://saturn_notebook.mpl")

import matplotlib.pyplot as plt
import io
import os
import sys
import time
from base64 import standard_b64encode
from . import utils
from more_itertools import peekable

_GRAPHICS_QUERY_ID = b'31'
_GRAPHICS_QUERY = b'\033_Gi=31,s=1,v=1,a=q,t=d,f=24;AAAA\033\\\033[c'
_DEVICE_ATTRIBUTES_RESPONSE_CHARS = b'?0123456789;'

enabled = None
seen = []

def _env_enables_kitty_graphics():
    return os.environ.get('TERM') == 'xterm-kitty' or 'WEZTERM_PANE' in os.environ

def _output_isatty(fd = None):
    try:
        return sys.stdout.isatty() if fd is None else os.isatty(fd)
    except (AttributeError, OSError, ValueError):
        return False

def _output_fd(fd = None):
    if fd is not None:
        return fd
    try:
        return sys.stdout.fileno()
    except (AttributeError, OSError, ValueError):
        return None

def _open_terminal_input_fd():
    try:
        if sys.stdin.isatty():
            return sys.stdin.fileno(), False
    except (AttributeError, OSError, ValueError):
        pass

    try:
        return os.open('/dev/tty', os.O_RDONLY | getattr(os, 'O_NOCTTY', 0)), True
    except OSError:
        return None, False

def _kitty_graphics_query_succeeded(response):
    start = 0
    while True:
        start = response.find(b'\033_G', start)
        if start == -1:
            return None

        end = response.find(b'\033\\', start + 3)
        if end == -1:
            return None

        control, separator, message = bytes(response[start + 3:end]).partition(b';')
        if separator:
            for field in control.split(b','):
                key, _, value = field.partition(b'=')
                if key == b'i' and value == _GRAPHICS_QUERY_ID:
                    return message == b'OK'

        start = end + 2

def _saw_primary_device_attributes(response):
    start = 0
    while True:
        start = response.find(b'\033[', start)
        if start == -1:
            return False

        end = response.find(b'c', start + 2)
        if end == -1:
            return False

        if all(ch in _DEVICE_ATTRIBUTES_RESPONSE_CHARS for ch in response[start + 2:end]):
            return True

        start = end + 1

def _query_kitty_graphics_protocol(output_fd, timeout = 0.2):
    try:
        import select
        import termios
    except ImportError:
        return None

    input_fd, close_input_fd = _open_terminal_input_fd()
    if input_fd is None:
        return None

    previous_attrs = None
    try:
        previous_attrs = termios.tcgetattr(input_fd)
        query_attrs = previous_attrs[:]
        query_attrs[6] = previous_attrs[6][:]
        query_attrs[3] &= ~(termios.ICANON | termios.ECHO)
        query_attrs[6][termios.VMIN] = 0
        query_attrs[6][termios.VTIME] = 0
        termios.tcsetattr(input_fd, termios.TCSANOW, query_attrs)

        os.write(output_fd, _GRAPHICS_QUERY)
        response = bytearray()
        deadline = time.monotonic() + timeout
        saw_device_attributes = False

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                detected = _kitty_graphics_query_succeeded(response)
                return False if detected is None and saw_device_attributes else detected

            ready, _, _ = select.select([input_fd], [], [], remaining)
            if not ready:
                detected = _kitty_graphics_query_succeeded(response)
                return False if detected is None and saw_device_attributes else detected

            chunk = os.read(input_fd, 1024)
            if not chunk:
                detected = _kitty_graphics_query_succeeded(response)
                return False if detected is None and saw_device_attributes else detected

            response.extend(chunk)
            detected = _kitty_graphics_query_succeeded(response)
            saw_device_attributes = saw_device_attributes or _saw_primary_device_attributes(response)
            if detected is not None and saw_device_attributes:
                return detected
    except (OSError, termios.error, ValueError):
        return None
    finally:
        if previous_attrs is not None:
            try:
                termios.tcsetattr(input_fd, termios.TCSANOW, previous_attrs)
            except (OSError, termios.error):
                pass
        if close_input_fd:
            try:
                os.close(input_fd)
            except OSError:
                pass

def _kitty_graphics_enabled(fd = None):
    global enabled
    if not _output_isatty(fd):
        return False
    if enabled is None:
        output_fd = _output_fd(fd)
        detected = None if output_fd is None else _query_kitty_graphics_protocol(output_fd)
        enabled = _env_enables_kitty_graphics() if detected is None else detected
    return enabled

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
    if _kitty_graphics_enabled(fd):
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
