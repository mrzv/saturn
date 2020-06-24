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

console = Console()

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
def run(infn, outfn, clean: "run from scratch, ignoring checkpoints" = False, debug = False, dry_run = False, repl = False):
    if not outfn:
        outfn = infn

    if os.path.exists(infn):
        with open(infn) as f:
            cells = c.parse(f)
    else:
        cells = []

    output = lambda cell: show_console(cell, rule = debug, verbose = debug)

    nb = notebook.Notebook()
    nb.add(cells)

    if not clean:
        checkpoint = nb.find_checkpoint()
        if checkpoint is not None:
            console.print(Rule(f"Skipping to checkpoint {checkpoint}", style='magenta'))
            nb.skip(checkpoint, output)
            console.print(Rule('Resuming', style="magenta"))

    nb.process(output, lambda *args: console.print(Rule(*args)))

    if repl:
        run_repl(nb, output, outfn, dry_run)

    if not dry_run:
        nb.save(outfn)


def run_repl(nb, output, outfn = '', dry_run = True):
    def execute_line(line):
        cells = c.parse(io.StringIO(line))
        nb.add(cells)
        nb.process(output)

    repl = PythonReplWithExecute(
        execute = execute_line,
        get_globals=lambda: nb.g,
        get_locals=lambda: nb.l,
        vi_mode=False,
        history_filename=None,
        startup_paths=None,
    )

    # @repl.add_key_binding('c-s')
    # def _(event):
    #     if not dry_run:
    #         nb.save(outfn)

    repl.run()

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
