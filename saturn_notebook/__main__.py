import  os
import  argh
from    rich.console import Console
from    rich.rule    import Rule
from    rich.theme   import Theme
from    rich.style   import Style

import  io
from    atomicwrites import atomic_write
from    more_itertools import peekable

from    .           import cells as c, notebook
from    .repl       import PythonReplWithExecute
from    .image      import show_png

try:
    from mpi4py import MPI
    root = MPI.COMM_WORLD.Get_rank() == 0
    using_mpi = MPI.COMM_WORLD.Get_size() > 1
except ImportError:
    root = True
    using_mpi = False

# workaround for a bug in OpenMPI (or anything else that screws up the terminal size);
# see https://github.com/willmcgugan/rich/issues/127
import  shutil
width = None if shutil.get_terminal_size().columns != 0 else 80

theme = Theme({
    "variables":    Style.parse("yellow"),
    "warn":         Style.parse("yellow"),
    "affirm":       Style.parse("green"),
    "error":        Style.parse("red"),
    "cell-name":    Style.parse("yellow"),
})

console = Console(width = width, theme = theme)

def show_console(cell, rule = False, verbose = False, no_show = False):
    if rule:
        console.print(Rule(cell.type_name() if verbose else ''))

    if not no_show:
        cell.show_console(console)

    if not cell.empty() and not rule:
        console.print()

def show_html(cell, f):
    cell.show_html(f)

def show(fn: "input notebook",
         html: "save HTML to a file" = '',
         debug: "show debugging information" = False):
    """Show the contents of the notebook, without evaluating."""
    with open(fn) as f:
        cells = c.parse(f, show_only = True)

    output   = lambda cell: show_console(cell, rule = debug, verbose = debug)

    if html:
        f_html = open(html, 'w')
        output = lambda cell: show_html(cell, f_html)

        f_html.write('<html>\n')
        f_html.write('<head>\n')
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

@argh.arg('outfn', nargs='?')
@argh.arg('-n', '--dry-run')
def run(infn: "input notebook",
        outfn: "output notebook (if empty, input modified in place)",
        clean: "run from scratch, ignoring checkpoints" = False,
        auto_capture: "automatically capture images" = False,
        debug: "show debugging information" = False,
        dry_run: "don't save the processed notebook" = False,
        only_root_output: "suppress output everywhere but rank 0 (for MPI)" = False,
        repl: "run REPL after the notebook is processed" = False):
    """Run the notebook."""
    if not outfn:
        outfn = infn

    if os.path.exists(infn):
        with open(infn) as f:
            cells = c.parse(f)
    else:
        cells = []

    def output(cell):
        if root or (not only_root_output and type(cell) is c.OutputCell):
            show_console(cell, rule = debug, verbose = debug)

    def info(*args, **kw):
        if root:
            console.print(Rule(*args, **kw))

    nb = notebook.Notebook(name = infn, auto_capture = auto_capture)
    nb.add(cells)

    if not clean:
        checkpoint = nb.find_checkpoint()
        if checkpoint is not None:
            info(f"Skipping to checkpoint {checkpoint}", style='magenta')
            nb.skip(checkpoint, output)
            info('Resuming', style="magenta")

    try:
        nb.process(output, info)

        if repl:
            run_repl(nb, output, outfn, dry_run)
    except SystemExit:
        info("Caught SystemExit")
        nb.move_all_incoming()
    except:
        info("Caught exception, aborting")
        from .traceback import Traceback
        tb = Traceback(nb, debug = debug, width = console.width)

        console_tb = Console(record = True, width = 80, theme = theme)
        console_tb.print(tb)

        nb.skip_next_output()
        nb.append(c.OutputCell.from_string(console_tb.export_text()))
        nb.move_all_incoming()

    if not dry_run and root:
        nb.save(outfn)


def run_repl(nb, output, outfn = '', dry_run = True):
    if using_mpi:
        comm = MPI.COMM_WORLD

    def execute_line(line):
        if using_mpi and root:
            line = comm.bcast(line, root = 0)
        blank = c.Blanks()
        blank.append('\n')
        cells = [blank] + c.parse(io.StringIO(line))
        nb.add(cells)
        nb.process(output)

    if not root:
        while True:
            line = comm.bcast('', root = 0)
            if not line: return
            execute_line(line)

    repl = PythonReplWithExecute(
        execute = execute_line,
        get_globals=lambda: nb.g,
        get_locals=lambda: nb.l,
        vi_mode=False,
        history_filename=None,
        startup_paths=None,
    )

    # Add the code cells to history
    for cell in nb.cells:
        for line in cell.repl_history():
            repl.history.append_string(line)

    @repl.add_key_binding('c-o')
    def _(event):
        if not dry_run and root:
            nb.save(outfn)

    repl.run()

    if using_mpi:
        comm.bcast('', root = 0)

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
def image(infn: "input notebook", i: "image index", out: "output PNG filename"):
    """Extract an image from the notebook."""
    if i is not None and not out:
        console.print("Must specify output filename, if image is specified")
        return

    with open(infn) as f:
        cells = c.parse(f, show_only = True)

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
    print(f"Saturn {ver('saturn_notebook')}")
    for dep in ['wurlitzer', 'rich', 'ptpython',
                'dill', 'markdown', 'atomicwrites',
                'pygments', 'more_itertools', 'matplotlib']:
        print(f"   {dep} {ver(dep)}")

@argh.arg('outfn', nargs='?')
def rehash(infn: "input notebook",
           outfn: "output notebook (if empty, input modified in place)"):
    """Rehash all the code cells, updating the hashes stored with checkpoints and variable cells. (advanced)"""
    if not outfn:
        outfn = infn

    with open(infn) as f:
        cells = c.parse(f)

    nb = notebook.Notebook(name = infn)
    nb.add(cells)
    nb.rehash()

    nb.save(outfn)

def main():
    argh.dispatch_commands([show, run, clean, image, version, rehash])

if __name__ == '__main__':
    main()
