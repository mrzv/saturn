import sys, os, io, contextlib
from  wurlitzer         import pipes, STDOUT, Wurlitzer, _default_encoding
from  . import image

# From: https://stackoverflow.com/a/18854817/44738
def chunkstring(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))

class CompositeIO:
    def __init__(self):
        self.outer = [io.StringIO()]
        self.outfd = None

    def empty(self):
        if len(self.outer) > 1: return False
        self.outer[0].seek(0, io.SEEK_END)
        if self.outer[0].tell() > 0: return False
        return True

    def set_outfd(self, outfd):
        self.outfd = outfd

    def __iter__(self):
        return iter(self.outer)

    def write(self, s):
        self.outer[-1].write(s)
        if self.outfd is not None:
            os.write(self.outfd, s.encode(_default_encoding))

    def append_png(self, buf):
        self.outer.append(buf)
        self.outer.append(io.StringIO())
        if self.outfd is not None:
            image.show_png(buf, self.outfd)

@contextlib.contextmanager
def captured_passthrough():
    out = CompositeIO()
    w = Wurlitzer(stdout=out, stderr=STDOUT, encoding=_default_encoding)
    with w:
        out.set_outfd(w._save_fds['stdout'])
        yield out

def collapse_carriage_return(lines):
    result = []
    for line in lines:
        while True:
            up = line.find('\x1b[A')
            cr = line.find('\r')

            if up != -1:
                result.pop()
                line = line[up+1:]
            elif cr != -1:
                line = line[cr+1:]
            else:
                result.append(line)
                break

    return result

