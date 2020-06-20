#!/usr/bin/env python3

import  os
import  argh
from    rich.console import Console
from    rich.rule    import Rule
from    atomicwrites import atomic_write

import  hashlib

from    icecream import ic

from    lib import  evaluate, utils, cells as c, image

console = Console()

def show_console(cell, rule = False, verbose = False):
    if rule:
        console.print(Rule(cell.type_name() if verbose else ''))

    cell.show_console(console)

    if not rule:
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

class Hasher:
    def __init__(self):
        self.m = hashlib.sha256()

    def update(self, code):
        if type(code) is c.CodeCell:
            code = code.code()
        self.m.update(bytes(code, 'utf-8'))

    def digest(self):
        return self.m.digest()

def find_checkpoint(cells):
    m = Hasher()
    last = -1
    for i,cell in enumerate(cells):
        if type(cell) is c.CodeCell:
            m.update(cell)
        elif type(cell) is c.CheckpointCell:
            if cell.expected(m.digest()):
                last = i
            else:
                break
    return last

@argh.arg('outfn', nargs='?')
@argh.arg('-n', '--dry-run')
def run(infn, outfn, clean: "run from scratch, ignoring checkpoints" = False, debug = False, dry_run = False):
    if not outfn:
        outfn = infn

    with open(infn) as f:
        cells = c.parse(f)

    output = lambda cell: show_console(cell, rule = debug, verbose = debug)

    g = {}
    l = {}
    m = Hasher()
    new_cells = []
    def add_new_cell(cell):
        new_cells.append(cell)
        if not debug and not cell.display(): return
        output(cell)

    checkpoint = -1
    if not clean:
        checkpoint = find_checkpoint(cells)
        if checkpoint > 0:
            l       = cells[checkpoint].load()
            running = cells[checkpoint].expected_hash()
            console.print(Rule(f"Skipping to checkpoint {checkpoint}", style='magenta'))

    pairs = utils.pairwise(cells)
    for i, (cell, next_cell) in enumerate(pairs):
        add_new_cell(cell)
        if i <= checkpoint:
            if type(cell) is c.CodeCell:
                m.update(cell)
            if i == checkpoint:
                console.print(Rule('Resuming', style="magenta"))
            continue

        if type(cell) is c.CodeCell:
            with utils.stdIO() as out:
                code = cell.code()
                result = evaluate.exec_eval(code, g, l)

            m.update(code)

            # skip the next output cell
            if type(next_cell) is c.OutputCell:
                next(pairs)

            out.seek(0)
            out_lines = out.readlines()

            lines = []
            png   = None
            if out_lines:
                lines += out_lines
            if result is not None:
                lines.append(result.__repr__() + '\n')

                if image.is_mpl(result):
                    png = image.save_mpl_png()

            if lines or png:
                add_new_cell(c.OutputCell(lines, png))
        elif type(cell) is c.CheckpointCell:
            cell.dump(m.digest(), l)

    if not dry_run:
        with atomic_write(outfn, mode='w', overwrite=True) as f:
            save(f, new_cells)

def save(f, cells):
    for i,cell in enumerate(cells):
        for line in cell.save():
            f.write(line)
        if i < len(cells) - 1:      # no newline at the end
            f.write('\n')

if __name__ == '__main__':
    argh.dispatch_commands([show, run])
