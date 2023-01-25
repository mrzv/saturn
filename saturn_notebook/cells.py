from rich.markdown import Markdown
from rich.syntax   import Syntax
from rich.text     import Text
from rich.rule     import Rule
from rich.abc      import RichRenderable

from  itertools import chain
import base64
import io
import dill
import hashlib
from  more_itertools    import peekable

import html
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

import markdown

from . import utils
from . import image
from . import evaluate

import  zipfile, os

# Prefix for the filename inside an external zipfile
_zip_fn_prefix = 'name='

def hash_bytes(content):
    return hashlib.sha256(content).hexdigest()[:16]

class Cell:
    def __init__(self):
        self.lines_ = []

    def append(self, line):
        prefix = self.__class__._prefix
        line = line[len(prefix):]       # eat the prefix
        self.lines_.append(line)

    def save(self, external):
        prefix = self.__class__._prefix
        return [prefix + line for line in self.lines_]

    def parse(self, external, info):            # called after all the lines have been read
        pass

    def lines(self):
        return ''.join(self.lines_)

    def repl_history(self):
        return []

    @classmethod
    def display(cls):
        return True

    def empty(self):
        return not self.__class__.display()

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
        return '[cell-name]== ' + self.__class__.__name__ + ' ==[/cell-name]\n' + self.lines()

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

    def __init__(self):
        super().__init__()
        self.skippable = True
        self.hashable  = True

    def __rich__(self):
        if not self.lines_:
            return
        return Syntax('>>> ' + '... '.join(self.lines_).strip(), 'python')

    def append(self, line):
        super().append(line)
        if line.startswith('#no-skip#'):
            self.skippable = False
        if line.startswith('#no-hash#'):
            self.hashable = False

    def code(self):
        lines = self.lines()
        if len(lines) > 0 and lines[-1] == '\n':
            return lines[:-1]
        return lines

    def _render_html(self):
        return f"<div class='code'>{highlight(self.code(), PythonLexer(), HtmlFormatter())}</div>"

    def repl_history(self):
        return self.save(None)

class MarkdownCell(Cell):
    _prefix = '#m>'
    _name   = 'Markdown'

    def __rich__(self):
        return Markdown(self.lines())

    def _render_html(self):
        return "<div class='markdown'>" + markdown.markdown(''.join(line[1:] if line[0] == ' ' else line for line in self.lines_)) + "</div>"

class OutputCell(Cell):
    _prefix = '#o> '
    _name   = 'Output'

    def __init__(self, composite_ = None):
        super().__init__()
        if composite_ is None:
            self.composite_ = utils.CompositeIO()
        else:
            self.composite_ = composite_

    @staticmethod
    def from_string(s):
        cell = OutputCell()
        cell.composite_.write(s)
        return cell

    def parse(self, external, info):
        super().parse(external, info)
        pl = peekable(self.lines_)
        for line in pl:
            if not line.startswith('png'):
                self.composite_.write(line)
            else:
                if _zip_fn_prefix in line:
                    # take everything from name= to the end (-1 to not include \n)
                    fn = line[line.index(_zip_fn_prefix) + len(_zip_fn_prefix):-1]
                    if external:
                        if zipfile.Path(external, at=fn).exists():
                            png_content = external.read(fn)
                            self.composite_.append_png(png_content)
                        else:
                            # here and below, we use
                            # self.composite_.append_rich, instead of info, so
                            # that the message appears in place of the cell,
                            # rather than before any other cell is processed
                            self.composite_.append_rich(Rule(f"[warn]image hash [cyan]{fn}[/cyan] not found in the external archive [cyan]{external.filename}[/cyan][/warn]"))
                    else:
                        self.composite_.append_rich(Rule(f"[warn]image hash found, but no external file given ([cyan]{fn}[/cyan])[/warn]"))
                else:
                    png_content = [line[3:]]
                    while pl and pl.peek().startswith('png') and not pl.peek().startswith('png{{{'):
                        png_content.append(next(pl)[3:])
                    png_content = ''.join(png_content)
                    self.composite_.append_png(base64.b64decode(png_content))
        self.lines_.clear()

    def save(self, external):
        lines_ = []
        for x in self.composite_:
            if type(x) is io.StringIO:
                x.seek(0)
                lines_ += [self._prefix + line for line in utils.collapse_carriage_return(x)]
            else:
                if external:
                    fn = f"{hash_bytes(x)}.png"
                    with external.open(fn, 'w') as f:
                        f.write(x)
                    lines_ += [self._prefix + f'png {_zip_fn_prefix}{fn}\n']
                else:   # inline
                    content = base64.b64encode(x).decode('ascii')
                    lines_ += [self._prefix + 'png' + line + '\n' for line in chunk(content, 80, markers = True)]
        return lines_

    def empty(self):
        return self.composite_.empty()

    def show_console(self, console):
        for x in self.composite_:
            if type(x) is io.StringIO:
                if x.getvalue():
                    console.print(Text(x.getvalue()))
            elif type(x) is bytes:
                image.show_png(x)
            elif isinstance(x,RichRenderable):
                console.print(x)
            else:
                console.print(Rule("[error]didn't recognize cell type[/error]"))

    def _render_html(self):
        result = ""
        for x in self.composite_:
            if type(x) is io.StringIO:
                result += f"<div class='output'><pre>{html.escape(x.getvalue())}</pre>\n"
            else:
                result += f'<img src="data:image/png;base64,{base64.b64encode(x).decode("ascii")}"/>\n'
        result += "</div>"
        return result

class BreakCell(Cell):
    _prefix = '#---#'

    @classmethod
    def display(cls):
        return False

    @staticmethod
    def create():
        cell = BreakCell()
        cell.lines_ = ['\n']
        return cell


class REPLCell(Cell):
    _prefix = '#-REPL-#'

    @classmethod
    def display(cls):
        return False

class SaturnCell(Cell):
    _prefix = '#saturn>'

    _external_prefix = 'external='

    def parse(self, external, info):            # called after all the lines have been read
        super().parse(external, info)
        line = self.lines_[0]
        self.external_fn = ''
        if self._external_prefix in line:
            # take everything from external= to the end (-1 to not include \n)
            # eventually, we'll want a more elaborate support, once we have other kinds of metadata
            self.external_fn = line[line.index(self._external_prefix) + len(self._external_prefix):-1]

    @classmethod
    def display(cls):
        return False

class CheckpointCell(Cell):
    _prefix = '#chk>'
    _extension = '.chk'
    _warning_name = "checkpoint"

    def expected(self, h):
        if self.expected_hash() == None:
            return False
        else:
            return self.expected_hash() == h

    def expected_hash(self):
        if not hasattr(self, '_expected'):
            self._expected = dill.load(self._content)
        return self._expected

    def show_console(self, console):
        if hasattr(self, '_warning'):
            console.print(self._warning)

    def parse(self, external, info):
        if all(l.strip() == '' for l in self.lines_):
            self.lines_ = []

        if not self.lines_:
            self._expected = None
            return

        line = self.lines_[0]
        if _zip_fn_prefix in line:
            fn = line[line.index(_zip_fn_prefix) + len(_zip_fn_prefix):-1]
            if external:
                if zipfile.Path(external, at=fn).exists():
                    self._content = io.BytesIO(external.read(fn))
                else:
                    self._warning = Rule(f"[warn]{self._warning_name} hash [cyan]{fn}[/cyan] not found in the external archive [cyan]{external.filename}[/cyan][/warn]")
                    self._expected = None
            else:
                self._warning = Rule(f"[warn]{self._warning_name} hash found, but no external file given ([cyan]{fn}[/cyan])[/warn]")
                self._expected = None
        else:
            content = self.lines()
            content = base64.b64decode(content)
            self._content = io.BytesIO(content)

    def load(self):
        h = self.expected_hash()    # just to make sure it's been parsed
        assert h != None
        if not hasattr(self, '_locals'):
            self._locals = dill.load(self._content)
        return self._locals

    def dump(self, running, locals_):
        try:
            content = io.BytesIO()
            dill.dump(running, content)
            dill.dump(locals_, content)
            self._content = content
        except:
            self._content = None
            raise

    def save(self, external):
        if hasattr(self, '_content') and self._content:
            content = self._content.getvalue()
            if not external:
                content = base64.b64encode(content).decode('ascii')
                self.lines_ = [line + '\n' for line in chunk(content, 80, markers = True)]
            else:
                fn = f"{hash_bytes(content)}{self._extension}"
                with external.open(fn, 'w') as f:
                    f.write(content)
                self.lines_ = [f' {_zip_fn_prefix}{fn}\n']
        else:
            self.lines_ = ['']      # to keep the blank checkpoint cell
        return super().save(external)

    def replace_hash(self, running):
        if self.expected_hash() == None: return
        content = io.BytesIO()
        dill.dump(running, content)
        content.write(self._content.read())
        self._content = content

class VariableCell(CheckpointCell):
    _prefix = '#var>'
    _extension = '.var'
    _warning_name = "variable"

    def parse(self, external, info):
        self.variables = self.lines_[0]
        self.lines_ = self.lines_[1:]

        super().parse(external, info)

    def load(self, locals_):
        locals_['_var_cell_load'] = dill.load(self._content)
        evaluate.exec_eval(self.variables.strip() + ' = _var_cell_load', locals_, locals_)
        del locals_['_var_cell_load']

    def dump(self, running, locals_):
        content = io.BytesIO()
        dill.dump(running, content)
        dill.dump(evaluate.eval_expression(self.variables, locals_), content)
        self._content = content

    def header(self):
        return self.__class__._prefix + self.variables

    def save(self, external):
        lines_ = super().save(external)
        return [self.header()] + lines_

    def repl_history(self):
        return [self.header()]

# Captures blank lines between cells
class Blanks(Cell):
    _prefix = ''

    def show_console(self, console):
        pass

    def show_html(self, f):
        pass

    @classmethod
    def display(cls):
        return False

    @staticmethod
    def create(n):
        cell = Blanks()
        cell.lines_ = ['\n']*n
        return cell

cell_types = [MarkdownCell, OutputCell, BreakCell, CheckpointCell, VariableCell, REPLCell, SaturnCell]

def identify(line):
    for Type in chain(cell_types, [CodeCell]):        # CodeCell matches everything, so comes last
        if Type.identify(line):
            return Type

def chunk(content, width, markers = False):
    chunking = utils.chunkstring(content, 80)
    if markers:
        chunking = chain(['{{{'], chunking, ['}}}'])
    return chunking

def open_external(external_fn, show_only, info):
    if external_fn:
        if not os.path.exists(external_fn):
            if show_only:
                info(f"External zip archive [error]{external_fn}[/error] not found.", style='warn')
            return None

        return zipfile.ZipFile(external_fn, 'r')
    else:
        return None

def parse(f, external_fn, *, show_only = False, info = lambda *args, **kwargs: None):
    external = open_external(external_fn, show_only, info)

    def should_parse(cell):
        # skip check-point cells in show mode
        return not show_only or cell.display() or type(cell) is SaturnCell

    cells = []
    def cells_append(cell):
        nonlocal external, external_fn
        if len(cells) > 0 and should_parse(cells[-1]):
            cells[-1].parse(external, info)

            if type(cells[-1]) is SaturnCell:
                if not external_fn and cells[-1].external_fn:
                    external_fn = cells[-1].external_fn
                    external = open_external(external_fn, show_only, info)

        cells.append(cell)

    p = peekable(f)
    for line in p:
        # agglomerate empty lines into Blanks and either store as such or return to the CodeCell, if in the middle of one
        if not line.strip():
            blank = Blanks()
            blank.append(line)
            while p and not p.peek().strip():
                blank.append(next(p))

            if p and len(cells) > 0 and type(cells[-1]) is CodeCell and identify(p.peek()) is CodeCell:
                for line in blank.lines_:
                    cells[-1].append(line)
            else:
                cells_append(blank)

            continue

        Type = identify(line)

        if len(cells) == 0 or type(cells[-1]) is not Type:
            cells_append(Type())
        cells[-1].append(line)

    if len(cells) > 0:
        if should_parse(cells[-1]):
            cells[-1].parse(external, info)

    return cells
