#!/usr/bin/env python3

import  os
import  argh
from    rich.console import Console
from    rich.rule    import Rule

import  io

from    prompt_toolkit import PromptSession
from    pygments.lexers.python import PythonLexer
from    prompt_toolkit.lexers import PygmentsLexer
from    prompt_toolkit.key_binding import KeyBindings
from    prompt_toolkit.shortcuts import message_dialog

from    icecream import ic

from    lib import  cells as c, notebook

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

    nb.process(output)

    if repl:
        run_repl(nb, output, outfn, dry_run)

    if not dry_run:
        nb.save(outfn)

def run_repl(nb, output, outfn = '', dry_run = True):
    session = PromptSession()

    # Swap enter and meta+enter #
    kb = KeyBindings()

    @kb.add('escape', 'enter')
    def _(event):
        event.current_buffer.insert_text('\n')

    @kb.add('enter')
    def _(event):
        event.current_buffer.validate_and_handle()

    @kb.add('c-s')
    def _(event):
        if not dry_run:
            nb.save(outfn)
    #############################

    while True:
        try:
            code = session.prompt('>>> ',
                                  lexer = PygmentsLexer(PythonLexer),
                                  key_bindings = kb,
                                  multiline = True,
                                  bottom_toolbar = None if not dry_run else 'Dry-run mode')
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        else:
            cells = c.parse(io.StringIO(code))
            nb.add(cells)
            nb.process(output)

if __name__ == '__main__':
    argh.dispatch_commands([show, run])
