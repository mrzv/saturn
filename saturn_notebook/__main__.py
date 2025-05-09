import  os, sys
import  argh
from    rich.console import Console
from    rich.rule    import Rule
from    rich.panel   import Panel

import  io
from    atomicwrites import atomic_write
from    more_itertools import peekable

from    contextlib import nullcontext

from    .           import cells as c, notebook
from    .repl       import PythonReplWithExecute
from    .image      import show_png

root = True
using_mpi = False

skip_repl = False

# workaround for a bug in OpenMPI (or anything else that screws up the terminal size);
# see https://github.com/willmcgugan/rich/issues/127
import  shutil
width = None if shutil.get_terminal_size().columns != 0 else 80

from    .theme      import theme
console = Console(width = width, theme = theme)

argv = []

def info(*args, block = False, **kw):
    if root:
        if not block:
            console.print(Rule(*args, **kw))
        else:
            console.print(*args, **kw)

def error(*args, **kw):
    if root:
        console.print(Panel(*args, **kw, style='error'))

def warn(*args, **kw):
    if root:
        console.print(Panel(*args, **kw, style='warn'))

def show_console(cell, rule = False, verbose = False, no_show = False):
    if rule:
        console.print(Rule(cell.type_name() if verbose else ''))

    if not no_show:
        cell.show_console(console)

def show_html(cell, f):
    cell.show_html(f)

katex_preamble = r"""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.3/dist/katex.min.css" integrity="sha384-Juol1FqnotbkyZUT5Z7gUPjQ9gzlwCENvUZTpQBAPxtusdwFLRy382PSDx5UUJ4/" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.3/dist/katex.min.js" integrity="sha384-97gW6UIJxnlKemYavrqDHSX3SiygeOwIZhwyOKRfSaf0JWKRVj9hLASHgFTzT+0O" crossorigin="anonymous"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.3/dist/contrib/auto-render.min.js" integrity="sha384-+VBxd3r6XgURycqtZ117nYw44OOcIax56Z4dCRWbxyPt0Koah1uHoK0o4+/RRE05" crossorigin="anonymous"></script>
<script>
    document.addEventListener("DOMContentLoaded", function() {
        renderMathInElement(document.body, {
          // customised options
          // • auto-render specific keys, e.g.:
          delimiters: [
              {left: '$$', right: '$$', display: true},
              {left: '$', right: '$', display: false},
              {left: '\\(', right: '\\)', display: false},
              {left: '\\[', right: '\\]', display: true}
          ],
          // • rendering keys, e.g.:
          throwOnError : false
        });
    });
</script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.3/dist/contrib/copy-tex.min.js" integrity="sha384-ww/583aHhxWkz5DEVn6OKtNiIaLi2iBRNZXfJRiY1Ai7tnJ9UXpEsyvOITVpTl4A" crossorigin="anonymous"></script>
"""

def show(fn: "input notebook",
         html: "save HTML to a file" = '',
         katex: "include KaTeX in HTML output" = False,
         external: "external zip archive with binary content" = '',
         debug: "show debugging information" = False):
    """Show the contents of the notebook, without evaluating."""

    if not os.path.exists(fn):
        console.print(f"No such file: [error]{fn}[/error]")
        return

    with open(fn) as f:
        cells = c.parse(f, external, show_only = True, info=info)
    _show(cells, html, katex, debug)

def _show(cells, html, katex, debug):
    output   = lambda cell: show_console(cell, rule = debug, verbose = debug)

    if html:
        f_html = open(html, 'w')
        output = lambda cell: show_html(cell, f_html)

        f_html.write('<!DOCTYPE html>\n')
        f_html.write('<html>\n')
        f_html.write('<head>\n')
        f_html.write('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/light.css">\n')
        f_html.write('<style> .muted { color: gray; } </style>')
        if katex:
            f_html.write(katex_preamble)
        f_html.write('<style>\n')
        f_html.write(c.HtmlFormatter().get_style_defs('.highlight'))
        f_html.write('</style>\n')
        f_html.write('</head>\n')
        f_html.write('<body>\n')


    for i,cell in enumerate(cells):
        if not cell.display(): continue
        output(cell)

    if html:
        f_html.write('</body>\n')
        f_html.write('</html>\n')

@argh.arg('infn', nargs='?')
@argh.arg('outfn', nargs='?')
@argh.arg('--no-mpi')
@argh.arg('-n', '--dry-run')
@argh.arg('-i', '--interactive')
def run(infn: "input notebook",
        outfn: "output notebook (if empty, input modified in place)",
        clean: "run from scratch, ignoring checkpoints" = False,
        auto_capture: "automatically capture images" = False,
        external: "external zip archive with binary content" = '',
        debug: "show debugging information" = False,
        no_mpi: "disable MPI awareness" = False,
        dry_run: "don't save the processed notebook" = False,
        only_root_output: "suppress output everywhere but rank 0 (for MPI)" = False,
        interactive: "run REPL after the notebook is processed" = False):
    """Run the notebook."""

    global using_mpi
    global root

    if not no_mpi:
        try:
            from mpi4py import MPI
            root = MPI.COMM_WORLD.Get_rank() == 0
            using_mpi = MPI.COMM_WORLD.Get_size() > 1
        except:
            pass

    if infn and os.path.exists(infn):
        with open(infn) as f:
            cells = c.parse(f, external, info=info)
    else:
        cells = []
        if outfn and not dry_run:
            warn(f"Input file [error]{infn}[/error] doesn't exist, but given an output file [cyan]{outfn}[/cyan]; forcing [affirm]--dry-run[/affirm]")
            dry_run = True

    if not infn:
        interactive = True

    if not outfn:
        outfn = infn

    sys.argv = [infn] + argv

    def output(cell):
        if root or (not only_root_output and type(cell) is c.OutputCell):
            show_console(cell, rule = debug, verbose = debug)

    nb = notebook.Notebook(name = infn, auto_capture = auto_capture, dry_run = dry_run)
    nb.add(cells)

    if not clean:
        checkpoint = nb.find_checkpoint()
        if checkpoint is not None:
            info(f"Skipping to checkpoint {checkpoint}", style='magenta')
            nb.skip(checkpoint, output)
            info('Resuming', style="magenta")

    try:
        sys.path.insert(0, os.path.dirname(infn))
        nb.process_all(output,
                       run_repl=lambda: run_repl(nb, output, debug=debug,
                                             prefix = [c.Blanks.create(1)], suffix = [c.Blanks.create(1), c.BreakCell.create()]),
                       force=interactive, info=info, debug=debug)

        if interactive:
            result = run_repl(nb, output, debug=debug)
            if result and not nb.dry_run and not outfn:
                from prompt_toolkit import prompt
                from prompt_toolkit.completion import PathCompleter
                outfn = prompt("Notebook filename (empty to not save): ", completer = PathCompleter())
                if outfn and not external:
                    external = prompt("External zip archive filename (empty to inline): ", completer = PathCompleter())
    except:
        nb.move_all_incoming()

    if not nb.dry_run and root and outfn:
        nb.save(outfn, external)


def run_repl(nb, output, debug = False,
             prefix = [c.Blanks.create(1), c.BreakCell.create(), c.Blanks.create(1)],
             suffix = []):
    if skip_repl:
        return

    if using_mpi:
        from mpi4py import MPI
        comm = MPI.COMM_WORLD

    def execute_line(line):
        line += '\n'
        if using_mpi and root:
            line = comm.bcast(line, root = 0)
        cells = []
        if nb.current > 0:
            cells += prefix
        cells += c.parse(io.StringIO(line), None, info=info)
        cells += suffix

        nb.insert(cells)
        nb.process_to(nb.current + len(cells),output,info=info, repl = True)

    if not root:
        while True:
            line = comm.bcast('', root = 0)
            if not line: return
            execute_line(line)

    saturn_dir = os.path.expanduser('~/.saturn')
    if not os.path.exists(saturn_dir):
        os.makedirs(saturn_dir)

    try:
        g = {}  # fake empty globals;
                # not specifying any get_globals throws an exception inside repl.run();
                # specifying nb.globals breaks checkpointing inside repl; not sure why
        repl = PythonReplWithExecute(
            execute = execute_line,
            get_globals=lambda: g,
            get_locals=lambda: nb.l,
            vi_mode=False,
            history_filename=saturn_dir + '/history',
            startup_paths=None,
            debug=debug,
        )
    except Exception as e:
        print("Caught exception setting up REPL:", e)
        raise

    # Add the code cells to history
    for cell in nb.cells:
        for line in cell.repl_history():
            repl.history.append_string(line)

    result = True

    @repl.add_key_binding('c-q')
    def _(event):
        nonlocal result
        event.app.exit(exception=EOFError)
        result = False

    # TODO: think about changing this to a toggle
    @repl.add_key_binding('f10')
    def _(event):
        nonlocal result
        nb.dry_run = True
        event.app.exit(exception=EOFError)
        result = False

    @repl.add_key_binding('c-w')
    def _(event):
        global skip_repl
        skip_repl = True
        event.app.exit(exception=EOFError)

    try:
        repl.run()
    except Exception as e:
        print("Caught exception in REPL:", e)
        raise

    if using_mpi:
        comm.bcast('', root = 0)

    return result

@argh.arg('outfn', nargs='?')
def clean(infn: "input notebook",
          outfn: "output notebook (if empty, input modified in place)",
          strip_output: "also strip all output" = False):
    """Remove all binary data from the notebook."""
    if not outfn:
        outfn = infn

    if os.path.exists(infn):
        with atomic_write(outfn, mode='w', overwrite=True) as of:
            with open(infn) as f:
                pf = peekable(f)
                for line in pf:
                    if strip_output and line.startswith('#o>'): continue
                    if line.startswith('#o> png'): continue
                    if line.startswith('#chk>') and line.strip() != '#chk>':
                        of.write('#chk>\n')
                        while pf and pf.peek().startswith('#chk>'):
                            next(pf)
                        continue
                    if line.startswith('#var>'):
                        # Keep the first line, but skip all subsequent lines
                        while pf and pf.peek().startswith('#var>'):
                            next(pf)
                    of.write(line)

@argh.arg('i',   nargs='?', type=int)
@argh.arg('out', nargs='?')
def image(infn: "input notebook", i: "image index", out: "output PNG filename",
          external: "external zip archive with binary content" = '',
          ):
    """Extract an image from the notebook."""
    if i is not None and not out:
        console.print("Must specify output filename, if image is specified")
        return

    with open(infn) as f:
        cells = c.parse(f, external, show_only = True, info=info)

    count = 0
    for cell in cells:
        if type(cell) is not c.OutputCell: continue

        for x in cell.composite_:
            if type(x) is io.StringIO: continue

            if i is None:
                print(f"{count}:")
                show_png(x)
            elif i == count:
                with open(out, 'wb') as f:
                    f.write(x)

            count += 1

def version():
    """Show version of Saturn and its dependencies."""
    from importlib_metadata import version as ver
    console.print(f"Saturn [version]{ver('saturn_notebook')}[/version] (Python {sys.version})")
    for dep in ['wurlitzer', 'rich', 'ptpython',
                'dill', 'markdown', 'atomicwrites',
                'pygments', 'more_itertools', 'matplotlib', 'nbformat']:
        try:
            console.print(f"   {dep} [version]{ver(dep)}[/version]")
        except:
            console.print(f"   {dep} [error]not found[/error]")

@argh.arg('outfn', nargs='?')
def convert(infn: "Jupyter notebook",
            outfn: "output notebook (if empty, show the cells instead)",
            version: "notebook version" = 4,
            external: "external zip archive with binary content" = '',
            html: "save HTML to a file" = '',
            katex: "include KaTeX in HTML output" = False,
            debug: "show debugging information" = False):
    """Convert a Jupyter notebook into a Saturn notebook."""
    import nbformat
    jnb = nbformat.read(infn, as_version=version)

    header = c.CodeCell()
    header.lines_ = ['# vim: ft=python foldmethod=marker foldlevel=0\n']
    cells = [header]

    for jcell in jnb.cells:
        if jcell['cell_type'] == 'markdown':
            cell = c.MarkdownCell()
            cell.lines_ = [' ' + line + '\n' if len(line) else '\n' for line in jcell['source'].split('\n')]
            if type(cells[-1]) is not c.Blanks:
                cells.append(c.Blanks.create(1))
            cells.append(cell)
            cells.append(c.Blanks.create(1))
        elif jcell['cell_type'] == 'code':
            if type(cells[-1]) is c.CodeCell:
                cells.append(c.Blanks.create(1))
                cells.append(c.BreakCell.create())
                cells.append(c.Blanks.create(1))
            cell = c.CodeCell()
            cell.lines_ = [line + '\n' for line in jcell['source'].split('\n')]
            cells.append(cell)

            for out in jcell['outputs']:
                if out['output_type'] == 'stream':
                    cell = c.OutputCell.from_string(out['text'])
                    cells.append(cell)
                elif out['output_type'] in ['display_data', 'execute_result']:
                    if 'image/png' in out['data']:
                        cell = c.OutputCell()
                        png_content = out['data']['image/png']
                        cell.composite_.append_png(c.base64.b64decode(png_content))
                        cells.append(cell)
                    elif 'text/plain' in out['data']:
                        cell = c.OutputCell.from_string(out['data']['text/plain'])
                        cells.append(cell)
                    else:
                        info('Unrecognized data type', style="magenta")
                else:
                    info('Unrecognized output type', style="magenta")
        else:
            info('Unrecognized cell type', style="magenta")

    if not outfn:
        _show(cells, html, katex, debug)
    else:
        nb = notebook.Notebook(name = outfn)
        nb.add(cells)
        nb.move_all_incoming()
        nb.save(outfn, external)


@argh.arg('outfn', nargs='?')
def rehash(infn: "input notebook",
           outfn: "output notebook (if empty, input modified in place)",
           external: "external zip archive with binary content" = ''):
    """Rehash all the code cells, updating the hashes stored with checkpoints and variable cells. (advanced)"""
    if not outfn:
        outfn = infn

    with open(infn) as f:
        cells = c.parse(f, external, info=info)

    nb = notebook.Notebook(name = infn)
    nb.add(cells)
    nb.rehash()

    nb.save(outfn, external)

@argh.arg('outfn', nargs='?')
def extract(infn: "input notebook",
            external: "external zip archive with binary content",
            outfn: "output notebook (if empty, input modified in place)"):
    """Extract embedded binary content into external zip archive."""
    if not outfn:
        outfn = infn

    with open(infn) as f:
        cells = c.parse(f, '', info=info)       # read without external

    nb = notebook.Notebook(name = infn)
    nb.add(cells)
    nb.move_all_incoming()

    nb.save(outfn, external)

@argh.arg('outfn', nargs='?')
def embed(infn: "input notebook",
          external: "external zip archive with binary content",
          outfn: "output notebook (if empty, input modified in place)"):
    """Embed binary content from external zip archive into notebook body."""
    if not outfn:
        outfn = infn

    with open(infn) as f:
        cells = c.parse(f, external, info=info)

    nb = notebook.Notebook(name = infn)
    nb.add(cells)
    nb.move_all_incoming()

    nb.save(outfn, '')      # write without external

@argh.arg('--no-mpi')
@argh.arg('-n', '--dry-run')
def _run(clean: "run from scratch, ignoring checkpoints" = False,
        auto_capture: "automatically capture images" = False,
        external: "external zip archive with binary content" = '',
        debug: "show debugging information" = False,
        no_mpi: "disable MPI awareness" = False,
        dry_run: "don't save the processed notebook" = False,
        only_root_output: "suppress output everywhere but rank 0 (for MPI)" = False):
    """Launch Saturn REPL."""
    run('', '', clean, auto_capture, external, debug, no_mpi, dry_run, only_root_output, True)

def main():
    global argv

    parser = argh.ArghParser()
    parser.set_default_command(_run)

    if '--' in sys.argv:
        idx = sys.argv.index('--')
        argv = sys.argv[idx+1:]
        sys.argv = sys.argv[:idx]
    parser.add_commands([show, run, clean, image, version, convert, rehash, extract, embed])
    parser.dispatch()

if __name__ == '__main__':
    main()
