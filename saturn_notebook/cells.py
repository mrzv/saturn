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
import pickletools
from  more_itertools    import peekable

import html
import binascii
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

import markdown
from urllib.parse import urlsplit

from . import utils
from . import image
from . import evaluate

import  zipfile, os, zlib

# Prefix for the filename inside an external zipfile
_zip_fn_prefix = 'name='
MAX_EXTERNAL_MEMBER_BYTES = 100 * 1024 * 1024
EXTERNAL_READ_ERRORS = (KeyError, ValueError, RuntimeError, OSError, zipfile.BadZipFile, zlib.error)

def hash_bytes(content):
    return hashlib.sha256(content).hexdigest()[:16]

def safe_archive_name(name):
    return name and not os.path.isabs(name) and os.path.normpath(name) == name and os.path.dirname(name) == ''


def external_has_name(external, name):
    return name in external.namelist()


def read_external_member(external, name):
    info = external.getinfo(name)
    if info.file_size > MAX_EXTERNAL_MEMBER_BYTES:
        raise ValueError(f"archive member is too large ({info.file_size} bytes)")
    return external.read(info)


def decode_folded_base64(content):
    lines = content.splitlines()
    if lines and lines[0].strip() == '{{{':
        lines = lines[1:]
    if lines and lines[-1].strip() == '}}}':
        lines = lines[:-1]
    return base64.b64decode(''.join(lines), validate=True)


_base64_re = re.compile(r"[A-Za-z0-9+/=]+")


def external_png_line(line):
    return line.startswith(f'png {_zip_fn_prefix}')


def inline_png_line(line):
    if line.startswith('png{{{'):
        return True
    if not line.startswith('png') or line.startswith('png ') or line.strip() == 'png':
        return False
    content = ''.join(line[3:].split())
    return bool(content) and len(content) % 4 == 0 and _base64_re.fullmatch(content) is not None


def png_output_line(line):
    return external_png_line(line) or inline_png_line(line)


def first_pickle_end(content):
    for opcode, _, position in pickletools.genops(content):
        if opcode.name == 'STOP':
            return position + 1
    raise ValueError("pickle stream has no STOP opcode")

class Cell:
    def __init__(self):
        self.lines_ = []
        self.line_save_indents = []
        self.save_indent = ''

    def append(self, line):
        prefix = self.__class__._prefix
        line = line[len(prefix):]       # eat the prefix
        self.lines_.append(line)
        self.line_save_indents.append(getattr(self, '_pending_save_indent', self.save_indent))
        if hasattr(self, '_pending_save_indent'):
            del self._pending_save_indent

    def save(self, external):
        prefix = self.__class__._prefix
        if len(self.line_save_indents) == len(self.lines_):
            return [save_indent + prefix + line for save_indent,line in zip(self.line_save_indents, self.lines_)]
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
        return self.lines_[:]

class MarkdownCell(Cell):
    _prefix = '#m>'
    _name   = 'Markdown'

    def __rich__(self):
        return Markdown(self.lines())

    def _render_html(self):
        content = ''.join(line[1:] if line.startswith(' ') else line for line in self.lines_)
        return "<div class='markdown'>" + sanitize_markdown_html(markdown.markdown(html.escape(content))) + "</div>"


_safe_url_schemes = {'', 'http', 'https', 'mailto'}
_url_attr_re = re.compile(r"\b(href|src)=(['\"])(.*?)\2", re.IGNORECASE | re.DOTALL)
_url_ignored_chars_re = re.compile(r"[\x00-\x20\x7f]")


def sanitize_markdown_html(rendered):
    def sanitize_url_attr(match):
        attr = match.group(1)
        quote = match.group(2)
        value = html.unescape(match.group(3)).strip()
        normalized = _url_ignored_chars_re.sub('', value)
        scheme = urlsplit(normalized).scheme.lower()
        raw_scheme = value[:value.find(':')] if scheme else ''
        if scheme not in _safe_url_schemes or _url_ignored_chars_re.search(raw_scheme):
            return f'{attr}={quote}#{quote}'
        return match.group(0)

    return _url_attr_re.sub(sanitize_url_attr, rendered)

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
            if not png_output_line(line):
                self.composite_.write(line)
            else:
                if external_png_line(line):
                    # take everything from name= to the end (-1 to not include \n)
                    fn = line[line.index(_zip_fn_prefix) + len(_zip_fn_prefix):-1]
                    if not safe_archive_name(fn):
                        self.composite_.append_rich(Rule(f"[warn]unsafe image archive name [cyan]{fn}[/cyan] ignored[/warn]"))
                    elif external:
                        if external_has_name(external, fn):
                            try:
                                png_content = read_external_member(external, fn)
                            except EXTERNAL_READ_ERRORS as e:
                                self.composite_.append_rich(Rule(f"[warn]image hash [cyan]{fn}[/cyan] could not be read from the external archive [cyan]{external.filename}[/cyan]: {e}[/warn]"))
                            else:
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
                    if line.startswith('png{{{'):
                        while pl and pl.peek().startswith('png'):
                            next_png = next(pl)
                            png_content.append(next_png[3:])
                            if next_png.startswith('png}}}'):
                                break
                    else:
                        while pl and inline_png_line(pl.peek()) and not pl.peek().startswith('png{{{'):
                            png_content.append(next(pl)[3:])
                    png_content = ''.join(png_content)
                    try:
                        self.composite_.append_png(decode_folded_base64(png_content))
                    except (binascii.Error, ValueError):
                        self.composite_.append_rich(Rule("[warn]invalid inline image content ignored[/warn]"))
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
                result += f"<div class='output'><pre>{html.escape(x.getvalue())}</pre>\n</div>\n"
            elif isinstance(x, bytes):
                result += f'<img src="data:image/png;base64,{base64.b64encode(x).decode("ascii")}"/>\n'
            elif isinstance(x, RichRenderable):
                title = getattr(x, 'title', x)
                result += f"<div class='muted'><pre>{html.escape(str(title))}</pre></div>\n"
            else:
                result += f"<div class='muted'><pre>{html.escape(str(x))}</pre></div>\n"
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
                    try:
                        self._content = io.BytesIO(read_external_member(external, fn))
                    except EXTERNAL_READ_ERRORS as e:
                        self._warning = Rule(f"[warn]{self._warning_name} hash [cyan]{fn}[/cyan] could not be read from the external archive [cyan]{external.filename}[/cyan]: {e}[/warn]")
                        self._expected = None
                else:
                    self._warning = Rule(f"[warn]{self._warning_name} hash [cyan]{fn}[/cyan] not found in the external archive [cyan]{external.filename}[/cyan][/warn]")
                    self._expected = None
            else:
                self._warning = Rule(f"[warn]{self._warning_name} hash found, but no external file given ([cyan]{fn}[/cyan])[/warn]")
                self._expected = None
        else:
            content = self.lines()
            try:
                content = decode_folded_base64(content)
            except (binascii.Error, ValueError):
                self._warning = Rule(f"[warn]invalid inline {self._warning_name} content ignored[/warn]")
                self._expected = None
            else:
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
        if not hasattr(self, '_content') or not self._content:
            return
        original = self._content.getvalue()
        try:
            payload_start = first_pickle_end(original)
        except ValueError:
            return
        content = io.BytesIO()
        dill.dump(running, content)
        content.write(original[payload_start:])
        self._content = content
        self._expected = running

    def header(self):
        return self.__class__._prefix

    def _render_html(self):
        return f'<div class="muted"><pre>{self.header()}</pre></div>'

class VariableCell(CheckpointCell):
    _prefix = '#var>'
    _extension = '.var'
    _warning_name = "variable"
    _metadata_kind = "saturn-variable-cache"

    def parse(self, external, info):
        if not self.lines_:
            self.variables = ''
            self._expected = None
            return
        self.variables = self.lines_[0]
        self.lines_ = self.lines_[1:]

        super().parse(external, info)

    def cache_metadata(self, running):
        return {
            'kind': self._metadata_kind,
            'hash': running,
            'variables': self.variables.strip(),
        }

    def metadata(self):
        metadata = CheckpointCell.expected_hash(self)
        return metadata if isinstance(metadata, dict) else None

    def expected_hash(self):
        metadata = self.metadata()
        if metadata and metadata.get('kind') == self._metadata_kind:
            return metadata.get('hash')
        return CheckpointCell.expected_hash(self)

    def expected(self, h):
        metadata = self.metadata()
        if not metadata or metadata.get('kind') != self._metadata_kind:
            return False
        return metadata.get('hash') == h and metadata.get('variables') == self.variables.strip()

    def load(self, locals_):
        self.expected_hash()
        if not hasattr(self, '_value'):
            self._value = dill.load(self._content)
        locals_['_var_cell_load'] = self._value
        evaluate.exec_eval(self.variables.strip() + ' = _var_cell_load', locals_, locals_)
        del locals_['_var_cell_load']

    def dump(self, running, locals_):
        content = io.BytesIO()
        dill.dump(self.cache_metadata(running), content)
        dill.dump(evaluate.exec_eval(self.variables.strip(), locals_, locals_), content)
        self._content = content

    def replace_hash(self, running):
        if not hasattr(self, '_content') or not self._content:
            return
        original = self._content.getvalue()
        try:
            payload_start = first_pickle_end(original)
        except ValueError:
            return
        content = io.BytesIO()
        dill.dump(self.cache_metadata(running), content)
        content.write(original[payload_start:])
        self._content = content
        self._expected = self.cache_metadata(running)

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


def is_main_guard_test(test):
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    if not isinstance(test.left, ast.Name) or test.left.id != '__name__':
        return False
    comparator = test.comparators[0]
    return isinstance(comparator, ast.Constant) and comparator.value == '__main__'


def is_main_guard(line):
    if line != line.lstrip():
        return False
    try:
        tree = ast.parse(line.rstrip('\n') + '\n    pass\n')
    except SyntaxError:
        return False
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.If):
        return False
    return is_main_guard_test(tree.body[0].test)


def main_guard_spans(lines):
    try:
        tree = ast.parse(''.join(lines))
    except SyntaxError:
        return {}

    spans = {}
    for node in tree.body:
        if not isinstance(node, ast.If) or not is_main_guard_test(node.test) or not node.body:
            continue
        spans[node.lineno - 1] = node
    return spans


def indentation(line):
    return len(leading_indent(line))


def leading_indent(line):
    return line[:len(line) - len(line.lstrip(' \t'))]


def dedent_line(line, amount):
    if not line.strip():
        return line
    return line[amount:] if indentation(line) >= amount else line.lstrip(' \t')


class ParsedLine:
    def __init__(self, line, save_indent = '', line_save_indent = None):
        self.line = line
        self.save_indent = save_indent
        self.line_save_indent = save_indent if line_save_indent is None else line_save_indent


def append_main_body_line(expanded, line, body_indent, body_prefix):
    if line.strip() and indentation(line) >= body_indent:
        expanded.append(ParsedLine(dedent_line(line, body_indent), body_prefix, body_prefix))
    else:
        expanded.append(ParsedLine(line, body_prefix, ''))


def expand_main_block_heuristic(lines, start, expanded):
    i = start
    line = lines[i]
    expanded.append(RawCell.create([line]))
    i += 1
    while i < len(lines) and not lines[i].strip():
        expanded.append(ParsedLine(lines[i]))
        i += 1
    if i == len(lines):
        return i

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
    return i


def expand_main_blocks(lines):
    spans = main_guard_spans(lines)
    expanded = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not is_main_guard(line):
            expanded.append(ParsedLine(line))
            i += 1
            continue

        node = spans.get(i)
        if not node:
            i = expand_main_block_heuristic(lines, i, expanded)
            continue

        expanded.append(RawCell.create([line]))
        body_start = node.body[0].lineno - 1
        body_end = max(getattr(child, 'end_lineno', child.lineno) for child in node.body) - 1
        body_prefix = leading_indent(lines[body_start])
        body_indent = len(body_prefix)

        i += 1
        while i < body_start:
            expanded.append(ParsedLine(lines[i]))
            i += 1

        while body_end + 1 < len(lines):
            next_line = lines[body_end + 1]
            if next_line.strip() and indentation(next_line) < body_indent:
                break
            body_end += 1

        while i <= body_end:
            append_main_body_line(expanded, lines[i], body_indent, body_prefix)
            i += 1

        if node.orelse:
            branch_end = getattr(node, 'end_lineno', i) or i
            if i < branch_end:
                expanded.append(RawCell.create(lines[i:branch_end]))
                i = branch_end
    return expanded

def open_external(external_fn, show_only, info, external_base = ''):
    if external_fn:
        if not os.path.isabs(external_fn) and external_base:
            external_fn = os.path.join(external_base, external_fn)
        if not os.path.exists(external_fn):
            if show_only:
                info(f"External zip archive [error]{external_fn}[/error] not found.", style='warn')
            return None

        try:
            return zipfile.ZipFile(external_fn, 'r')
        except zipfile.BadZipFile:
            info(f"External zip archive [error]{external_fn}[/error] is not a valid zip file.", style='warn')
            return None
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
                blank.save_indent = parsed.save_indent
                blank._pending_save_indent = parsed.line_save_indent
                blank.append(line)
                while p and not isinstance(p.peek(), Cell) and not p.peek().line.strip():
                    parsed_blank = next(p)
                    blank._pending_save_indent = parsed_blank.line_save_indent
                    blank.append(parsed_blank.line)

                if p and not isinstance(p.peek(), Cell) and len(cells) > 0 and type(cells[-1]) is CodeCell and identify(p.peek().line) is CodeCell:
                    for line,save_indent in zip(blank.lines_, blank.line_save_indents):
                        cells[-1]._pending_save_indent = save_indent
                        cells[-1].append(line)
                else:
                    cells_append(blank)

                continue

            Type = identify(line)

            if len(cells) == 0 or type(cells[-1]) is not Type or getattr(cells[-1], 'save_indent', '') != parsed.save_indent:
                cells_append(Type())
                cells[-1].save_indent = parsed.save_indent
            cells[-1]._pending_save_indent = parsed.line_save_indent
            cells[-1].append(line)

        if len(cells) > 0:
            if should_parse(cells[-1]):
                cells[-1].parse(external, info)
    finally:
        if external:
            external.close()

    return cells
