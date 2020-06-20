import  hashlib
import  io
from    atomicwrites import atomic_write

from    . import cells as c, utils, evaluate, image

class Hasher:
    def __init__(self):
        self.m = hashlib.sha256()

    def update(self, code):
        if type(code) is c.CodeCell:
            code = code.code()
        self.m.update(bytes(code, 'utf-8'))

    def digest(self):
        return self.m.digest()

class Notebook:
    def __init__(self, debug = False):
        self.debug = debug

        self.incoming = []
        self.current  = 0

        self.cells = []

        self.g = {}
        self.l = {}
        self.m = Hasher()

    def add(self, cells):
        self.incoming += cells

    def skip(self, location, output = lambda x: None):
        while self.current < location:
            cell = self.incoming[self.current]
            if type(cell) is c.CodeCell:
                self.m.update(cell)
            self.append(cell, output)
            self.current += 1

        cell = self.incoming[self.current]
        assert type(cell) is c.CheckpointCell
        self.l = cell.load()
        self.append(cell, output)
        self.current += 1

    def process(self, output):
        while self.current < len(self.incoming):
            cell = self.incoming[self.current]
            self.current += 1

            if self.current < len(self.incoming):
                next_cell = self.incoming[self.current]
            else:
                next_cell = None

            self.append(cell, output)

            if type(cell) is c.CodeCell:
                with utils.stdIO() as out:
                    code = cell.code()
                    result = evaluate.exec_eval(code, self.g, self.l)

                self.m.update(code)

                # skip the next output cell
                if type(next_cell) is c.OutputCell:
                    self.current += 1

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
                    self.append(c.OutputCell(lines, png), output)
            elif type(cell) is c.CheckpointCell:
                cell.dump(self.m.digest(), self.l)

    def append(self, cell, output = lambda x: None):
        self.cells.append(cell)
        if not self.debug and not cell.display(): return
        output(cell)

    def save(self, fn):
        with atomic_write(fn, mode='w', overwrite=True) as f:
            for i,cell in enumerate(self.cells):
                for line in cell.save():
                    f.write(line)
                if i < len(self.cells) - 1:      # no newline at the end
                    f.write('\n')

    def find_checkpoint(self):
        m = Hasher()
        last = None
        for i,cell in enumerate(self.incoming):
            if type(cell) is c.CodeCell:
                m.update(cell)
            elif type(cell) is c.CheckpointCell:
                if cell.expected(m.digest()):
                    last = i
                else:
                    break
        return last
