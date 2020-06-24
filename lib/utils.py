import sys, io, contextlib

# From: https://stackoverflow.com/a/18854817/44738
def chunkstring(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))

class CompositeIO:
    def __init__(self):
        self.outer = [io.StringIO()]

    def empty(self):
        if len(self.outer) > 1: return False
        if self.outer[0].getvalue(): return False
        return True

    def __iter__(self):
        return iter(self.outer)

    def write(self, s):
        self.outer[-1].write(s)

    def append_png(self, buf):
        self.outer.append(buf)
        self.outer.append(io.StringIO())
