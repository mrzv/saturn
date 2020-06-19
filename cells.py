from rich.markdown import Markdown
from rich.syntax   import Syntax

import itertools
import base64
import io
import dill

import utils

from icecream import ic

class Cell:
    def __init__(self):
        self.lines = []

    def append(self, line):
        prefix = self.__class__._prefix
        line = line[len(prefix):]       # eat the prefix
        self.lines.append(line)

    def save(self):
        prefix = self.__class__._prefix
        return [prefix + line for line in self.lines]

    def parse(self):            # called after all the lines have been read
        self.trim()

    def display(self):
        return True

    def trim(self):
        for bg, l in enumerate(self.lines):
            if l.strip():
                break
        else:
            bg += 1
        for end, l in enumerate(self.lines[::-1]):
            if l.strip():
                break
        else:
            end += 1
        end = len(self.lines) - end
        self.lines = self.lines[bg:end]

    @classmethod
    def identify(cls, line):
        return line.startswith(cls._prefix)

    def type_name(self):
        if hasattr(self.__class__, '_name'):
            return self.__class__._name
        else:
            return self.__class__.__name__

    def __repr__(self):
        return '== ' + self.__class__.__name__ + '\n' + ''.join(self.lines)

    def __rich__(self):
        return '[yellow]== ' + self.__class__.__name__ + ' ==[/yellow]\n' + ''.join(self.lines)

class CodeCell(Cell):
    _prefix = ''
    _name   = 'Code'

    def __rich__(self):
        return Syntax(''.join('>>> ' + l for l in self.lines if l), 'python')

    def code(self):
        return ''.join(self.lines)

class MarkdownCell(Cell):
    _prefix = '#m#'
    _name   = 'Markdown'

    def __rich__(self):
        return Markdown(''.join(self.lines))

class OutputCell(Cell):
    _prefix = '#o# '
    _name   = 'Output'

    def __init__(self, lines = None):
        if lines is None:
            self.lines = []
        else:
            self.lines = lines

    def __rich__(self):
        return ''.join('--> ' + l for l in self.lines)

class BreakCell(Cell):
    _prefix = '#-#'

    def display(self):
        return False

    def save(self):
        return self._prefix + '\n'

class CheckpointCell(Cell):
    _prefix = '#chk#'

    def expected(self, h):
        if self._expected == None:
            return False
        else:
            return self._expected == h

    def expected_hash(self):
        assert self._expected != None
        return self._expected

    def display(self):
        return False

    def parse(self):
        super().parse()

        if not self.lines:
            self._expected = None
            return

        content = ''.join(self.lines)
        content = base64.b64decode(content)

        self._expected, self._locals = dill.load(io.BytesIO(content))

    def load(self):
        assert self._expected != None
        return self._locals

    def dump(self, running, locals_):
        content = io.BytesIO()
        dill.dump((running, locals_), content)
        content.seek(0)
        content = content.read()
        content = base64.b64encode(content).decode('ascii')
        self.lines = [line + '\n' for line in utils.chunkstring(content, 80)]

cell_types = [MarkdownCell, OutputCell, BreakCell, CheckpointCell]

def identify(line):
    for Type in itertools.chain(cell_types, [CodeCell]):        # CodeCell matches everything, so comes last
        if Type.identify(line):
            return Type

def parse(f):
    cells = []

    for line in f:
        Type = identify(line)
        if len(cells) == 0 or type(cells[-1]) is not Type:
            if len(cells) > 0:
                cells[-1].parse()
            cell = Type()
            cells.append(cell)
        cells[-1].append(line)

    if len(cells) > 0:
        cells[-1].parse()

    return cells
