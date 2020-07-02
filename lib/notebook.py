import  hashlib
import  io
from    atomicwrites import atomic_write
from    wurlitzer    import pipes, STDOUT

from    . import cells as c, utils, evaluate, image, mpl

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
    def __init__(self, auto_capture = False, debug = False):
        self.auto_capture = auto_capture
        self.debug = debug

        self.incoming = []
        self.current  = 0

        self.cells = []

        self.g = {}
        self.l = self.g
        self.m = Hasher()

    def add(self, cells):
        self.incoming += cells

    def skip(self, location, output = lambda x: None):
        while self.current < location:
            cell = self.incoming[self.current]
            if type(cell) is c.CodeCell:
                if cell.skippable:
                    self.m.update(cell)
                else:
                    self.execute(cell, output)
            self.append(cell, output)
            self.current += 1

        cell = self.incoming[self.current]
        assert type(cell) is c.CheckpointCell
        self.g = cell.load()
        self.l = self.g
        self.append(cell, output)
        self.current += 1

    def next_cell(self):
        if self.current < len(self.incoming):
            return self.incoming[self.current]
        else:
            return None

    def execute(self, cell, output, info = lambda *args: None):
        # skip blanks, if any
        while type(self.next_cell()) is c.Blanks:
            self.append(self.next_cell())
            self.current += 1

        code = cell.code()
        self.m.update(code)

        if type(self.next_cell()) is c.VariableCell:
            if self.next_cell().expected(self.m.digest()):
                info(f"Previous code cell not evaluated, loading [yellow]{self.next_cell().variables.strip()}[/yellow] instead")
                self.next_cell().load(self.l)
                self.append(self.next_cell(), output)
                self.current += 1
                return

        with utils.captured_passthrough() as out:
            mpl.figures = out

            result = evaluate.exec_eval(code, self.g, self.l)
            if result is not None:
                out.write(result.__repr__() + '\n')
                if self.auto_capture and image.is_new_mpl_available():
                    out.append_png(image.save_mpl_png())

        if type(self.next_cell()) is c.VariableCell:
              self.next_cell().dump(self.m.digest(), self.l)
              self.append(self.next_cell(), output)
              self.current += 1

        # skip the next output cell
        if type(self.next_cell()) is c.OutputCell:
            self.current += 1

        self.append(c.OutputCell(out), lambda cell: None)
        print()

    def process(self, output, info = lambda *args: None):
        while self.current < len(self.incoming):
            cell = self.incoming[self.current]
            self.current += 1

            self.append(cell, output)

            if type(cell) is c.CodeCell:
                self.execute(cell, output, info)
            elif type(cell) is c.VariableCell:
                cell.dump(self.m.digest(), self.l)
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
                if i != len(self.cells) - 1 and not line.endswith('\n'):
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
