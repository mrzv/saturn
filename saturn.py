#!/usr/bin/env python3

import  os
import  argh
from    rich.console import Console
from    rich.rule    import Rule

import  io
from    atomicwrites import atomic_write
from    more_itertools import peekable

from    lib         import cells as c, notebook
from    lib.repl    import PythonReplWithExecute

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
console = Console(width = width)

def show_console(cell, rule = False, verbose = False):
    if rule:
        console.print(Rule(cell.type_name() if verbose else ''))

    cell.show_console(console)

    if not cell.empty() and not rule:
        console.print()

def show_html(cell, f):
    cell.show_html(f)

def show(fn, html = '', debug = False):
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
def run(infn, outfn,
        clean: "run from scratch, ignoring checkpoints" = False,
        auto_capture: "automatically capture images" = False,
        debug = False,
        dry_run = False,
        only_root_output = False,
        repl = False):
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

    nb = notebook.Notebook(auto_capture = auto_capture)
    nb.add(cells)

    if not clean:
        checkpoint = nb.find_checkpoint()
        if checkpoint is not None:
            info(f"Skipping to checkpoint {checkpoint}", style='magenta')
            nb.skip(checkpoint, output)
            info('Resuming', style="magenta")

    nb.process(output, info)

    if repl:
        run_repl(nb, output, outfn, dry_run)

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

    comm.bcast('', root = 0)

@argh.arg('outfn', nargs='?')
def clean(infn, outfn):
    """Remove all binary data from the notebook."""
    if not outfn:
        outfn = infn

    if os.path.exists(infn):
        with atomic_write(outfn, mode='w', overwrite=True) as of:
            with open(infn) as f:
                pf = peekable(f)
                for line in pf:
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


if __name__ == '__main__':
    argh.dispatch_commands([show, run, clean])
