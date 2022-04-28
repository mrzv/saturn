from rich.traceback import Traceback as RichTraceback, Stack, PathHighlighter, WINDOWS, _SyntaxError
from rich.highlighter   import ReprHighlighter
from rich.padding   import Padding
from rich.console   import RenderResult, group as render_group
from rich.text      import Text
from rich.syntax    import Syntax


# Patch Traceback to print Syntax from cells rather than from_path
class Traceback(RichTraceback):
    def __init__(self, nb, debug = False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.nb = nb

        if not debug:
            # skip past exec_eval
            for i,stack in enumerate(self.trace.stacks):
                eval_location = next((j for j,x in enumerate(stack.frames) if x.name == 'exec_eval'), None)
                if eval_location is not None:
                    self.trace.stacks[i].frames = stack.frames[eval_location+1:]

    @staticmethod
    def filename_cell(fn):
        colon_pos = fn.rfind(':')
        if colon_pos == -1:
            return fn, -1
        filename = fn[:colon_pos]
        cell_id = int(fn[colon_pos+1:])
        return filename, cell_id

    @render_group()
    def _render_stack(self, stack: Stack) -> RenderResult:
        path_highlighter = PathHighlighter()
        theme = self.theme or ("fruity" if WINDOWS else "monokai")
        for frame in stack.frames:
            filename, cell_id = self.filename_cell(frame.filename)
            if cell_id != -1:
                text = Text.assemble(
                    (" File ", "traceback.text"),
                    (f'"{filename}"', "traceback.filename"),
                    (", cell ", "traceback.text"),
                    (f"{cell_id}", "traceback.lineno"),
                    (", line ", "traceback.text"),
                    (str(frame.lineno), "traceback.lineno"),
                    (", in ", "traceback.text"),
                    (frame.name, "traceback.name"),
                )
            else:
                text = Text.assemble(
                    (" File ", "traceback.text"),
                    (f'"{filename}"', "traceback.filename"),
                    (", line ", "traceback.text"),
                    (str(frame.lineno), "traceback.lineno"),
                    (", in ", "traceback.text"),
                    (frame.name, "traceback.name"),
                )
            yield path_highlighter(text)
            if frame.filename.startswith("<"):
                continue
            try:
                if cell_id != -1:
                    syntax = Syntax(
                        self.nb.cells[cell_id].code(),
                        'python',
                        theme=theme,
                        line_numbers=True,
                        line_range=(
                            frame.lineno - self.extra_lines,
                            frame.lineno + self.extra_lines,
                        ),
                        highlight_lines={frame.lineno},
                        word_wrap=self.word_wrap,
                    )
                else:
                    syntax = Syntax.from_path(
                        filename,
                        theme=theme,
                        line_numbers=True,
                        line_range=(
                            frame.lineno - self.extra_lines,
                            frame.lineno + self.extra_lines,
                        ),
                        highlight_lines={frame.lineno},
                        word_wrap=self.word_wrap,
                    )
            except Exception:
                raise
            else:
                yield Padding.indent(syntax, 2)
