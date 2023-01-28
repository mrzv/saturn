import  hashlib
import  io
import  zipfile
from    contextlib import nullcontext
from    atomicwrites import atomic_write
from    wurlitzer    import pipes, STDOUT

from    rich.console import Console

from    . import cells as c, utils, evaluate, image, mpl

from    .traceback import Traceback
from    .theme     import theme

class Hasher:
    def __init__(self):
        self.m = hashlib.sha256()

    def update(self, cell):
        if not cell.hashable: return
        code = cell.code()
        self.m.update(bytes(code, 'utf-8'))

    def digest(self):
        return self.m.digest()

class Notebook:
    def __init__(self, *, name = '', auto_capture = False, debug = False, dry_run = False):
        self.name = name
        self.auto_capture = auto_capture
        self.debug = debug
        self.dry_run = dry_run

        self.incoming = []
        self.current  = 0

        self.cells = []

        self.g = {'__name__' : '__main__'}
        self.l = self.g
        self.m = Hasher()

    def __len__(self):
        return len(self.cells) + len(self.incoming)

    def add(self, cells):
        self.incoming += cells

    def insert(self, cells):
        self.incoming = self.incoming[:self.current] + cells + self.incoming[self.current:]

    def skip(self, location, output = lambda x: None):
        while self.current < location:
            cell = self.incoming[self.current]
            self.append(cell, output)
            self.current += 1
            if type(cell) is c.CodeCell:
                if cell.skippable:
                    self.m.update(cell)
                else:
                    self.execute(cell, output)

        cell = self.incoming[self.current]
        assert type(cell) is c.CheckpointCell
        self.g = cell.load()
        self.l = self.g
        self.append(cell, output)
        self.current += 1

    def move_all_incoming(self):
        while self.current < len(self.incoming):
            cell = self.incoming[self.current]
            self.cells.append(cell)
            self.current += 1

    def next_cell(self):
        if self.current < len(self.incoming):
            return self.incoming[self.current]
        else:
            return None

    def execute(self, cell, output, info = lambda *args: None):
        cell_id = len(self.cells) - 1
        cell_id_display = len([x for x in self.cells if type(x) is c.CodeCell]) # human-readable display only counts code cells

        # figure out the range of cells that belong to the current cell
        begin = self.current
        while type(self.next_cell()) in [c.Blanks, c.VariableCell, c.OutputCell]:
            self.current += 1
        # leave the last Blanks to MarkdownCell or BreakCell
        if type(self.next_cell()) in [c.MarkdownCell, c.BreakCell] and type(self.incoming[self.current-1]) is c.Blanks:
            self.current -= 1

        # reset back
        end = self.current
        self.current = begin

        # skip blanks, if any
        while type(self.next_cell()) is c.Blanks:
            if self.current >= end:
                break
            self.append(self.next_cell())
            self.current += 1

        self.m.update(cell)

        if type(self.next_cell()) is c.VariableCell:
            if self.next_cell().expected(self.m.digest()):
                info(f"Previous code cell not evaluated, [affirm]loading[/affirm] [variables]{self.next_cell().variables.strip()}[/variables] instead")
                self.next_cell().load(self.l)
                self.append(self.next_cell(), output)
                self.current += 1
                return

        with utils.captured_passthrough() as out:
            mpl.figures = out

            result = evaluate.exec_eval(cell.code(), self.g, self.l, name = f"{self.name}:{cell_id}:{cell_id_display}")
            if result is not None:
                out.write(repr(result) + '\n')
                if self.auto_capture and image.is_new_mpl_available():
                    out.append_png(image.save_mpl_png())

        if type(self.next_cell()) is c.VariableCell:
            try:
                self.next_cell().dump(self.m.digest(), self.l)
            except:
                info(f"[error]Failed[/error] to save varialbes [variables]{self.next_cell().variables.strip()}[/variables], [affirm]skipping[/affirm]")
                tb = Traceback(self, self.debug)
                info(tb, block = True)
                info(f"[affirm]continuing[/affirm]")
            self.append(self.next_cell(), output)
            self.current += 1

        # skip the next output cell
        self.skip_next_output()

        self.append(c.OutputCell(out), lambda cell: None)
        print()

    def skip_next_output(self):
        if type(self.next_cell()) is c.VariableCell:
            self.append(self.next_cell())
            self.current += 1
        if type(self.next_cell()) is c.OutputCell:
            self.current += 1

    def process_all(self, output, **kwargs):
        # Since extra cells may be added via REPL during the execution,
        # we need the outer loop to make sure everything is processed
        while self.current < len(self.incoming):
            self.process_to(len(self.incoming), output, **kwargs)

    def process_to(self, to, output, *, repl = lambda: None, force = False, debug = False, info = lambda *args, **kwargs: None):
        while self.current < to:
            cell = self.incoming[self.current]
            self.current += 1

            self.append(cell, output)

            if type(cell) is c.CodeCell:
                try:
                    self.execute(cell, output, info)
                except SystemExit:
                    info("Caught SystemExit")
                    raise       # SystemExit quits regardless of force
                except:
                    info("Caught exception")
                    tb = Traceback(self, debug = debug, width = 80)

                    console_tb = Console(record = True, width = 80, theme = theme)
                    console_tb.print(tb)

                    self.skip_next_output()
                    self.append(c.OutputCell.from_string(console_tb.export_text()))

                    if not force:
                        raise
            elif type(cell) is c.VariableCell:
                info(f"[warn]Warning:[/warn] isolated variable cell [variables]{cell.variables.strip()}[/variables]; result will never be used")
                try:
                    cell.dump(self.m.digest(), self.l)
                except:
                    info(f"[error]Failed[/error] to save variables [variables]{cell.variables.strip()}[/variables], [affirm]skipping[/affirm]")
                    tb = Traceback(self, self.debug)
                    info(tb, block = True)
                    info(f"[affirm]continuing[/affirm]")
            elif type(cell) is c.CheckpointCell:
                try:
                    cell.dump(self.m.digest(), self.l)
                except:
                    info(f"[error]Failed[/error] to save state in checkpoint cell, [affirm]skipping[/affirm]")
                    tb = Traceback(self, self.debug)
                    info(tb, block = True)
                    info(f"[affirm]continuing[/affirm]")
            elif type(cell) is c.REPLCell:
                if repl() == False:
                    raise SystemExit

    def append(self, cell, output = lambda x: None):
        self.cells.append(cell)
        if not self.debug and not cell.display(): return
        output(cell)

    def rehash(self):
        while self.current < len(self.incoming):
            cell = self.incoming[self.current]
            self.current += 1

            if type(cell) is c.CodeCell:
                self.m.update(cell)
            elif type(cell) is c.VariableCell or type(cell) is c.CheckpointCell:
                cell.replace_hash(self.m.digest())

            self.append(cell)

    def save(self, fn, external):
        if self.dry_run:
            return

        if not external:
            for cell in self.cells:
                if type(cell) is c.SaturnCell and cell.external_fn:
                    external = cell.external_fn
                    break

        with atomic_write(fn, mode='w', overwrite=True) as f:
            with zipfile.ZipFile(external, 'w') if external else nullcontext() as external_zip:
                for i,cell in enumerate(self.cells):
                    for line in cell.save(external_zip):
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
