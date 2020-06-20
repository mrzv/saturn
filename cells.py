from rich.markdown import Markdown
from rich.syntax   import Syntax

from  itertools import chain
import base64
import io
import dill

import html
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

import markdown

import utils
import image

from icecream import ic

class Cell:
    def __init__(self):
        self.lines_ = []

    def append(self, line):
        prefix = self.__class__._prefix
        line = line[len(prefix):]       # eat the prefix
        self.lines_.append(line)

    def save(self):
        prefix = self.__class__._prefix
        return [prefix + line for line in self.lines_]

    def parse(self):            # called after all the lines have been read
        self.trim()

    def lines(self):
        return ''.join(self.lines_)

    @classmethod
    def display(cls):
        return True

    def trim(self):
        for bg, l in enumerate(self.lines_):
            if l.strip():
                break
        else:
            bg += 1
        for end, l in enumerate(self.lines_[::-1]):
            if l.strip():
                break
        else:
            end += 1
        end = len(self.lines_) - end
        self.lines_ = self.lines_[bg:end]

    @classmethod
    def identify(cls, line):
        return line.startswith(cls._prefix)

    def type_name(self):
        if hasattr(self.__class__, '_name'):
            return self.__class__._name
        else:
            return self.__class__.__name__

    def __repr__(self):
        return '== ' + self.__class__.__name__ + '\n' + self.lines()

    def __rich__(self):
        return '[yellow]== ' + self.__class__.__name__ + ' ==[/yellow]\n' + self.lines()

    def show_console(self, console):
        console.print(self)

    def show_html(self, f):
        f.write(self._render_html())
        f.write('\n')

    def _render_html(self):
        return f"<div><h2>{self.__class__.__name__}</h2> <pre>{html.escape(self.lines())}</pre></div>"

class CodeCell(Cell):
    _prefix = ''
    _name   = 'Code'

    def __rich__(self):
        return Syntax(''.join('>>> ' + l for l in self.lines_ if l), 'python')

    def code(self):
        return self.lines()

    def _render_html(self):
        return f"<div class='code'>{highlight(self.code(), PythonLexer(), HtmlFormatter())}</div>"

class MarkdownCell(Cell):
    _prefix = '#m#'
    _name   = 'Markdown'

    def __rich__(self):
        return Markdown(self.lines())

    def _render_html(self):
        return "<div class='markdown'>" + markdown.markdown(''.join(line[1:] if line[0] == ' ' else line for line in self.lines_)) + "</div>"

class OutputCell(Cell):
    _prefix = '#o# '
    _name   = 'Output'

    def __init__(self, lines_ = None, png = None):
        if lines_ is None:
            self.lines_ = []
        else:
            self.lines_ = lines_

        self.png = png

    def parse(self):
        super().parse()

        png_content = [line[3:] for line in self.lines_ if line.startswith('png')]
        self.lines_  = [line for line in self.lines_ if not line.startswith('png')]

        if png_content:
            png_content = ''.join(png_content)
            self.png    = base64.b64decode(png_content)
        else:
            self.png = None

    def save(self):
        lines_ = super().save()

        if self.png:
            content = base64.b64encode(self.png).decode('ascii')
            lines_ += [self._prefix + 'png' + line + '\n' for line in chunk(content, 80, markers = True)]

        return lines_

    def __rich__(self):
        return ''.join('--> ' + l for l in self.lines_)

    def show_console(self, console):
        super().show_console(console)

        if self.png:
            image.show_png(self.png)

    def _render_html(self):
        result =  f"<div class='output'><pre>{html.escape(self.lines())}</pre>"

        if self.png:
            result += f'<img src="data:image/png;base64,{base64.b64encode(self.png).decode("ascii")}"/>'

        result += "</div>"

        return result

class BreakCell(Cell):
    _prefix = '#-#'

    @classmethod
    def display(cls):
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

    @classmethod
    def display(cls):
        return False

    def parse(self):
        super().parse()

        if not self.lines_:
            self._expected = None
            return

        content = self.lines()
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
        self.lines_ = [line + '\n' for line in chunk(content, 80, markers = True)]

cell_types = [MarkdownCell, OutputCell, BreakCell, CheckpointCell]

def identify(line):
    for Type in chain(cell_types, [CodeCell]):        # CodeCell matches everything, so comes last
        if Type.identify(line):
            return Type

def chunk(content, width, markers = False):
    chunking = utils.chunkstring(content, 80)
    if markers:
        chunking = chain(['{{{'], chunking, ['}}}'])
    return chunking

def parse(f, show_only = False):
    cells = []

    for line in f:
        Type = identify(line)

        if show_only and not Type.display(): continue     # skip check-point cells in show mode

        if len(cells) == 0 or type(cells[-1]) is not Type:
            if len(cells) > 0:
                cells[-1].parse()
            cell = Type()
            cells.append(cell)
        cells[-1].append(line)

    if len(cells) > 0:
        cells[-1].parse()

    return cells
