from rich.markdown import Markdown
from rich.syntax   import Syntax

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

    def trim(self):
        for bg, l in enumerate(self.lines):
            if l.strip():
                break
        for end, l in enumerate(self.lines[::-1]):
            if l.strip():
                break
        end = len(self.lines) - end
        self.lines = self.lines[bg:end]

    @classmethod
    def identify(cls, line):
        return line.startswith(cls._prefix)

    def type_name(self):
        return self.__class__.__name__

    def __repr__(self):
        return '== ' + self.__class__.__name__ + '\n' + ''.join(self.lines)

    def __rich__(self):
        return '[yellow]== ' + self.__class__.__name__ + ' ==[/yellow]\n' + ''.join(self.lines)

class CodeCell(Cell):
    _prefix = ''

    def __rich__(self):
        return Syntax(''.join('>>> ' + l for l in self.lines if l), 'python')

    def code(self):
        return ''.join(self.lines)

class MarkdownCell(Cell):
    _prefix = '#m#'

    def __rich__(self):
        return Markdown(''.join(self.lines))

class OutputCell(Cell):
    _prefix = '#o# '

    def __init__(self, lines = None):
        if lines is None:
            self.lines = []
        else:
            self.lines = lines

    def __rich__(self):
        return ''.join('--> ' + l for l in self.lines)

class BreakCell(Cell):
    _prefix = '#-#'

cell_types = [MarkdownCell, OutputCell, BreakCell]

cell_types.append(CodeCell)     # CodeCell matches everything, so must come last

def identify(line):
    for Type in cell_types:
        if Type.identify(line):
            return Type

def parse(f):
    cells = []

    for line in f:
        Type = identify(line)
        if len(cells) == 0 or type(cells[-1]) is not Type:
            if len(cells) > 0:
                cells[-1].trim()
            cell = Type()
            cells.append(cell)
        cells[-1].append(line)

    if len(cells) > 0:
        cells[-1].trim()

    return cells
