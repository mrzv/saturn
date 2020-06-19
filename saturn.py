#!/usr/bin/env python3

import  argh
from    rich.console import Console
from    rich.rule    import Rule
from    atomicwrites import atomic_write

from    icecream import ic

import  evaluate, utils
import  cells as c

console = Console()

def show_cell(cell, rule = False, verbose = False):
    output = console.print
    if rule:
        output(Rule(cell.type_name() if verbose else ''))
    # output()
    output(cell)
    if not rule:
        output()

def show(fn):
    with open(fn) as f:
        cells = c.parse(f)

    for i,cell in enumerate(cells):
        if type(cell) is c.BreakCell: continue
        show_cell(cell)

@argh.arg('outfn', nargs='?')
def run(infn, outfn):
    if not outfn:
        outfn = infn

    with open(infn) as f:
        cells = c.parse(f)

    output = console.print

    g = {}
    l = {}
    new_cells = []
    def add_new_cell(cell):
        new_cells.append(cell)
        if type(cell) is c.BreakCell: return
        show_cell(cell)

    pairs = utils.pairwise(cells)
    for cell, next_cell in pairs:
        add_new_cell(cell)

        if type(cell) is c.CodeCell:
            with utils.stdIO() as out:
                code = cell.code()
                result = evaluate.exec_eval(code, g, l)

            # skip the next output cell
            if type(next_cell) is c.OutputCell:
                next(pairs)

            out.seek(0)
            out_lines = out.readlines()

            lines = []
            if out_lines:
                lines += out_lines
            if result is not None:
                lines.append(result.__repr__() + '\n')

            if lines:
                add_new_cell(c.OutputCell(lines))

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
