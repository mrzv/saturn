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
import ast
import re
from  more_itertools    import peekable

import html
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

import markdown
from urllib.parse import urlsplit

from . import utils
from . import image
from . import evaluate

import  zipfile, os

# Prefix for the filename inside an external zipfile
_zip_fn_prefix = 'name='

def hash_bytes(content):
    return hashlib.sha256(content).hexdigest()[:16]

def safe_archive_name(name):
    return name and not os.path.isabs(name) and os.path.normpath(name) == name and os.path.dirname(name) == ''


def external_has_name(external, name):
    return name in external.namelist()

class Cell:
    def __init__(self):
        self.lines_ = []
        self.save_indent = ''

    def append(self, line):
        prefix = self.__class__._prefix
        line = line[len(prefix):]       # eat the prefix
        self.lines_.append(line)

    def save(self, external):
        prefix = self.__class__._prefix
        return [self.save_indent + prefix + line for line in self.lines_]

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
        content = ''.join(line[1:] if line.startswith(' ') else line for line in self.lines_)
        return "<div class='markdown'>" + sanitize_markdown_html(markdown.markdown(html.escape(content))) + "</div>"


_safe_url_schemes = {'', 'http', 'https', 'mailto'}


def sanitize_markdown_html(rendered):
    def sanitize_url_attr(match):
        attr = match.group(1)
        quote = match.group(2)
        value = html.unescape(match.group(3)).strip()
        scheme = urlsplit(value).scheme.lower()
        if scheme not in _safe_url_schemes:
            return f'{attr}={quote}#{quote}'
        return match.group(0)

    return re.sub(r"\b(href|src)=(['\"])(.*?)\2", sanitize_url_attr, rendered, flags=re.IGNORECASE)

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
                    if not safe_archive_name(fn):
                        self.composite_.append_rich(Rule(f"[warn]unsafe image archive name [cyan]{fn}[/cyan] ignored[/warn]"))
                    elif external:
                        if external_has_name(external, fn):
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
            if isinstance(x, io.StringIO):
                x.seek(0)
                lines_ += [self.save_indent + self._prefix + line for line in utils.collapse_carriage_return(x)]
            else:
                if external:
                    fn = f"{hash_bytes(x)}.png"
                    with external.open(fn, 'w') as f:
                        f.write(x)
                    lines_ += [self.save_indent + self._prefix + f'png {_zip_fn_prefix}{fn}\n']
                else:   # inline
                    content = base64.b64encode(x).decode('ascii')
                    lines_ += [self.save_indent + self._prefix + 'png' + line + '\n' for line in chunk(content, 80, markers = True)]
        return lines_

    def empty(self):
        return self.composite_.empty()

    def show_console(self, console):
        for x in self.composite_:
            if isinstance(x, io.StringIO):
                if x.getvalue():
                    console.print(Text(x.getvalue()), end='')
            elif isinstance(x, bytes):
                image.show_png(x)
            elif isinstance(x,RichRenderable):
                console.print(x)
            else:
                console.print(Rule("[error]didn't recognize cell type[/error]"))

    def _render_html(self):
        result = ""
        for x in self.composite_:
            if isinstance(x, io.StringIO):
                result += f"<div class='output'><pre>{html.escape(x.getvalue())}</pre>\n"
            elif isinstance(x, bytes):
                result += f'<img src="data:image/png;base64,{base64.b64encode(x).decode("ascii")}"/>\n'
            elif isinstance(x, RichRenderable):
                title = getattr(x, 'title', x)
                result += f"<div class='muted'><pre>{html.escape(str(title))}</pre></div>\n"
            else:
                result += f"<div class='muted'><pre>{html.escape(str(x))}</pre></div>\n"
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


class RawCell(Cell):
    _prefix = ''

    @staticmethod
    def create(lines):
        cell = RawCell()
        cell.lines_ = lines
        return cell

    @classmethod
    def display(cls):
        return False

class SaturnCell(Cell):
    _prefix = '#saturn>'

    _external_prefix = 'external='

    def parse(self, external, info):            # called after all the lines have been read
        super().parse(external, info)
        if not self.lines_:
            self.external_fn = ''
            return
        line = self.lines_[0]
        self.external_fn = ''
        if self._external_prefix in line:
            # take everything from external= to the end (-1 to not include \n)
            # eventually, we'll want a more elaborate support, once we have other kinds of metadata
            self.external_fn = line[line.index(self._external_prefix) + len(self._external_prefix):-1]

    @staticmethod
    def create(external_fn):
        cell = SaturnCell()
        cell.external_fn = external_fn
        return cell

    def save(self, external):
        if self.external_fn:
            self.lines_ = [f' {self._external_prefix}{self.external_fn}\n']
        return super().save(external)

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
            if not safe_archive_name(fn):
                self._warning = Rule(f"[warn]unsafe {self._warning_name} archive name [cyan]{fn}[/cyan] ignored[/warn]")
                self._expected = None
            elif external:
                if external_has_name(external, fn):
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
        if h is None:
            raise ValueError(f"Cannot load empty or invalid {self._warning_name} cell")
        if not hasattr(self, '_locals'):
            self._locals = dill.load(self._content)
        return self._locals

    def dump(self, running, locals_):
        try:
            content = io.BytesIO()
            dill.dump(running, content)
            dill.dump(locals_, content)
            self._content = content
        except Exception:
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

    def header(self):
        return self.__class__._prefix

    def _render_html(self):
        return f'<div class="muted"><pre>{self.header()}</pre></div>'

class VariableCell(CheckpointCell):
    _prefix = '#var>'
    _extension = '.var'
    _warning_name = "variable"

    def parse(self, external, info):
        if not self.lines_:
            self.variables = ''
            self._expected = None
            return
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
        dill.dump(evaluate.exec_eval(self.variables.strip(), locals_, locals_), content)
        self._content = content

    def header(self):
        return self.__class__._prefix + self.variables

    def save(self, external):
        lines_ = super().save(external)
        return [self.save_indent + self.header()] + lines_

    def repl_history(self):
        return [self.header()]

# Captures blank lines between cells
class Blanks(Cell):
    _prefix = ''

    def show_console(self, console):
        for line in self.lines_:
            console.print(line, end='')

    def show_html(self, f):
        pass

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


def is_main_guard(line):
    if line != line.lstrip():
        return False
    try:
        tree = ast.parse(line.rstrip('\n') + '\n    pass\n')
    except SyntaxError:
        return False
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.If):
        return False
    test = tree.body[0].test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    if not isinstance(test.left, ast.Name) or test.left.id != '__name__':
        return False
    comparator = test.comparators[0]
    return isinstance(comparator, ast.Constant) and comparator.value == '__main__'


def indentation(line):
    return len(leading_indent(line))


def leading_indent(line):
    return line[:len(line) - len(line.lstrip(' \t'))]


def dedent_line(line, amount):
    if not line.strip():
        return line
    return line[amount:] if indentation(line) >= amount else line.lstrip(' \t')


class ParsedLine:
    def __init__(self, line, save_indent = ''):
        self.line = line
        self.save_indent = save_indent


def expand_main_blocks(lines):
    expanded = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not is_main_guard(line):
            expanded.append(ParsedLine(line))
            i += 1
            continue

        expanded.append(RawCell.create([line]))
        i += 1
        while i < len(lines) and not lines[i].strip():
            expanded.append(ParsedLine(lines[i]))
            i += 1
        if i == len(lines):
            break

        body_prefix = leading_indent(lines[i])
        body_indent = len(body_prefix)
        while i < len(lines) and (not lines[i].strip() or indentation(lines[i]) >= body_indent):
            expanded.append(ParsedLine(dedent_line(lines[i], body_indent), body_prefix))
            i += 1

        while i < len(lines) and lines[i] == lines[i].lstrip() and lines[i].lstrip().startswith(('elif ', 'else:')):
            branch_lines = [lines[i]]
            i += 1
            while i < len(lines) and not lines[i].strip():
                branch_lines.append(lines[i])
                i += 1
            if i == len(lines):
                expanded.append(RawCell.create(branch_lines))
                break
            branch_indent = indentation(lines[i])
            while i < len(lines) and (not lines[i].strip() or indentation(lines[i]) >= branch_indent):
                branch_lines.append(lines[i])
                i += 1
            expanded.append(RawCell.create(branch_lines))
    return expanded

def open_external(external_fn, show_only, info, external_base = ''):
    if external_fn:
        if not os.path.isabs(external_fn) and external_base:
            external_fn = os.path.join(external_base, external_fn)
        if not os.path.exists(external_fn):
            if show_only:
                info(f"External zip archive [error]{external_fn}[/error] not found.", style='warn')
            return None

        return zipfile.ZipFile(external_fn, 'r')
    else:
        return None

def parse(f, external_fn, *, show_only = False, info = lambda *args, **kwargs: None, external_base = ''):
    external = open_external(external_fn, show_only, info, external_base)

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
                    external = open_external(external_fn, show_only, info, external_base)

        cells.append(cell)

    try:
        p = peekable(expand_main_blocks(list(f)))
        for parsed in p:
            if isinstance(parsed, Cell):
                cells_append(parsed)
                continue

            line = parsed.line
            # agglomerate empty lines into Blanks and either store as such or return to the CodeCell, if in the middle of one
            if not line.strip():
                blank = Blanks()
                blank.append(line)
                blank.save_indent = parsed.save_indent
                while p and not isinstance(p.peek(), Cell) and not p.peek().line.strip():
                    blank.append(next(p).line)

                if p and not isinstance(p.peek(), Cell) and len(cells) > 0 and type(cells[-1]) is CodeCell and identify(p.peek().line) is CodeCell:
                    for line in blank.lines_:
                        cells[-1].append(line)
                else:
                    cells_append(blank)

                continue

            Type = identify(line)

            if len(cells) == 0 or type(cells[-1]) is not Type or getattr(cells[-1], 'save_indent', '') != parsed.save_indent:
                cells_append(Type())
                cells[-1].save_indent = parsed.save_indent
            cells[-1].append(line)

        if len(cells) > 0:
            if should_parse(cells[-1]):
                cells[-1].parse(external, info)
    finally:
        if external:
            external.close()

    return cells
