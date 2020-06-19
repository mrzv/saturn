#!/usr/bin/env python3

import  os
import  argh
from    rich.console import Console
from    rich.rule    import Rule
from    atomicwrites import atomic_write

import  hashlib

from    icecream import ic

import  evaluate, utils
import  cells as c
import  image

console = Console()

def show_cell(cell, rule = False, verbose = False):
    output = console.print
    if rule:
        output(Rule(cell.type_name() if verbose else ''))
    # output()
    output(cell)
    if not rule:
        output()

def show(fn, debug = False):
    with open(fn) as f:
        cells = c.parse(f)

    for i,cell in enumerate(cells):
        if not cell.display(): continue
        show_cell(cell, rule = debug, verbose = debug)

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
def run(infn, outfn, debug = False, dry_run = False):
    if not outfn:
        outfn = infn

    show_images = image.enabled()

    with open(infn) as f:
        cells = c.parse(f)

    output = console.print

    g = {}
    l = {}
    m = Hasher()
    new_cells = []
    def add_new_cell(cell):
        new_cells.append(cell)
        if not debug and not cell.display(): return
        show_cell(cell, rule = debug, verbose = debug)

    checkpoint = find_checkpoint(cells)
    if checkpoint > 0:
        l       = cells[checkpoint].load()
        running = cells[checkpoint].expected_hash()
        output(Rule(f"Skipping to checkpoint {checkpoint}", style='magenta'))

    pairs = utils.pairwise(cells)
    for i, (cell, next_cell) in enumerate(pairs):
        add_new_cell(cell)
        if i <= checkpoint:
            if type(cell) is c.CodeCell:
                m.update(cell)
            if i == checkpoint:
                output(Rule('Resuming', style="magenta"))
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
            if out_lines:
                lines += out_lines
            if result is not None:
                lines.append(result.__repr__() + '\n')

                if show_images and image.display(result):
                    image.show()

            if lines:
                add_new_cell(c.OutputCell(lines))
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
