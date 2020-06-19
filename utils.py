import sys, io, contextlib

# From: https://stackoverflow.com/a/3906390/44738
@contextlib.contextmanager
def stdIO(stdout=None, stderr=None):
    old = sys.stdout

    if stdout is None:
        stdout = io.StringIO()

    sys.stdout = stdout
    yield stdout

    sys.stdout = old

from itertools import tee, chain
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(chain(iterable, [None]))
    next(b, None)
    return zip(a, b)
