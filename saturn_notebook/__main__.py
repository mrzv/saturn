import  os, sys
import  argh
from    rich.console import Console
from    rich.rule    import Rule
from    rich.panel   import Panel

import  io
from    atomicwrites import atomic_write
from    more_itertools import peekable

from    .           import cells as c, convert as jupyter_convert, html as saturn_html, mpi, notebook
from    .repl       import PythonReplWithExecute
from    .image      import show_png

root = True
using_mpi = False
mpi_comm = None

skip_repl = False

try:
    from . import viewer
    has_viewer = True
except ImportError:
    has_viewer = False


def require_viewer():
    if not has_viewer:
        raise RuntimeError("GUI support requires the viewer extra; install saturn-notebook[viewer]")

# workaround for a bug in OpenMPI (or anything else that screws up the terminal size);
# see https://github.com/willmcgugan/rich/issues/127
import  shutil
width = None if shutil.get_terminal_size().columns != 0 else 80

from    .theme      import theme
console = Console(width = width, theme = theme)

argv = []


def default_external_name(fn):
    base, _ = os.path.splitext(fn)
    return base + '.zip'


def save_external_name(outfn, external, inline):
    if external and inline:
        raise ValueError("--external and --inline cannot be used together")
    if inline or not outfn:
        return ''
    if external:
        if os.path.isabs(external):
            return external
        outdir = os.path.dirname(outfn)
        if outdir:
            return os.path.join(outdir, external)
        return external
    return default_external_name(outfn)

def info(*args, block = False, **kw):
    if root:
        if not block:
            console.print(Rule(*args, **kw))
        else:
            console.print(*args, **kw)

def error(*args, **kw):
    if root:
        console.print(Panel(*args, **kw, style='error'))

def warn(*args, **kw):
    if root:
        console.print(Panel(*args, **kw, style='warn'))

def show_console(cell, rule = False, verbose = False, no_show = False):
    if rule:
        console.print(Rule(cell.type_name() if verbose else ''))

    if not no_show:
        cell.show_console(console)

@argh.arg('fn', help="input notebook")
@argh.arg('--html', help="save HTML to a file")
@argh.arg('-k', '--katex', help="include KaTeX in HTML output")
@argh.arg('--standalone', help="inline CSS instead of linking CDN assets in HTML output")
@argh.arg('--external', help="external zip archive with binary content")
@argh.arg('-g', '--gui', help="view notebook in GUI")
@argh.arg('--debug', help="show debugging information")
def show(fn,
         html = '',
         *,
         katex = False,
         standalone = False,
         external = '',
         gui = False,
         debug = False):
    """Show the contents of the notebook, without evaluating."""

    if not os.path.exists(fn):
        console.print(f"No such file: [error]{fn}[/error]")
        return

    with open(fn) as f:
        cells = c.parse(f, external, show_only = True, info=info, external_base=os.path.dirname(fn))

    if gui:
        require_viewer()
        html = io.StringIO()
    _show(cells, html, katex, standalone, debug)
    if gui:
        viewer.view(html.getvalue())

def _show(cells, html, katex, standalone, debug):
    if html:
        saturn_html.render(cells, html, katex, standalone)
        return

    for cell in cells:
        if not cell.display(): continue
        show_console(cell, rule = debug, verbose = debug)

@argh.arg('infn', nargs='?', help="input notebook")
@argh.arg('outfn', nargs='?', help="output notebook (if empty, input modified in place)")
@argh.arg('-c', '--clean', help="run from scratch, ignoring checkpoints")
@argh.arg('-a', '--auto-capture', help="automatically capture images")
@argh.arg('-e', '--external', help="external zip archive with binary content")
@argh.arg('--inline', help="embed binary content inline instead of using an external archive")
@argh.arg('--force-external', help="replace an existing external archive even if it has no matching Saturn manifest")
@argh.arg('--debug', help="show debugging information")
@argh.arg('--no-mpi', help="disable MPI awareness")
@argh.arg('-n', '--dry-run', help="don't save the processed notebook")
@argh.arg('--only-root-output', help="suppress output everywhere but rank 0 (for MPI)")
@argh.arg('-i', '--interactive', help="run REPL after the notebook is processed")
def run(infn,
        outfn,
        clean = False,
        auto_capture = False,
        external = '',
        inline = False,
        force_external = False,
        debug = False,
        no_mpi = False,
        dry_run = False,
        only_root_output = False,
        interactive = False):
    """Run the notebook."""

    global using_mpi
    global root
    global mpi_comm

    mpi_state = mpi.detect(no_mpi)
    root = mpi_state.root
    using_mpi = mpi_state.using
    mpi_comm = mpi_state.comm

    if infn and os.path.exists(infn):
        with open(infn) as f:
            cells = c.parse(f, external, info=info, external_base=os.path.dirname(infn))
    else:
        cells = []
        if outfn and not dry_run:
            warn(f"Input file [error]{infn}[/error] doesn't exist, but given an output file [cyan]{outfn}[/cyan]; forcing [affirm]--dry-run[/affirm]")
            dry_run = True

    if not infn:
        interactive = True

    if not outfn:
        outfn = infn

    original_argv = sys.argv
    inserted_path = None
    sys.argv = [infn] + argv

    def output(cell):
        if root or (not only_root_output and isinstance(cell, c.OutputCell)):
            show_console(cell, rule = debug, verbose = debug)

    nb = notebook.Notebook(name = infn, auto_capture = auto_capture, dry_run = dry_run)
    nb.add(cells)

    if not clean:
        checkpoint = nb.find_checkpoint()
        if checkpoint is not None:
            info(f"Skipping to checkpoint {checkpoint}", style='magenta')
            nb.skip(checkpoint, output)
            info('Resuming', style="magenta")

    caught = None
    try:
        if infn:
            inserted_path = os.path.dirname(infn)
            sys.path.insert(0, inserted_path)
        nb.process_all(output,
                       run_repl=lambda: run_repl(nb, output, debug=debug,
                                               prefix = [c.Blanks.create(1)], suffix = [c.Blanks.create(1), c.BreakCell.create()]),
                       force=interactive, info=info, debug=debug)

        if interactive:
            result = run_repl(nb, output, debug=debug)
            if result and not nb.dry_run and not outfn:
                from prompt_toolkit import prompt
                from prompt_toolkit.completion import PathCompleter
                outfn = prompt("Notebook filename (empty to not save): ", completer = PathCompleter())
                if outfn and not external and not inline:
                    external = default_external_name(outfn)
    except BaseException:
        caught = sys.exc_info()
        nb.move_all_incoming()

    try:
        if not nb.dry_run and root and outfn:
            nb.save(outfn, save_external_name(outfn, external, inline), inline=inline, force_external=force_external)

        if caught:
            _, exc, tb = caught
            raise exc.with_traceback(tb)
    finally:
        sys.argv = original_argv
        if inserted_path is not None:
            if sys.path and sys.path[0] == inserted_path:
                sys.path.pop(0)
            else:
                try:
                    sys.path.remove(inserted_path)
                except ValueError:
                    pass


def run_repl(nb, output, debug = False,
             prefix = None,
             suffix = None):
    if prefix is None:
        prefix = [c.Blanks.create(1), c.BreakCell.create(), c.Blanks.create(1)]
    if suffix is None:
        suffix = []

    if skip_repl:
        return

    if using_mpi:
        comm = mpi_comm

    def execute_line(line):
        line += '\n'
        if using_mpi and root:
            line = comm.bcast(line, root = 0)
        cells = []
        if nb.current > 0:
            cells += prefix
        cells += c.parse(io.StringIO(line), None, info=info)
        cells += suffix

        nb.insert(cells)
        nb.process_to(nb.current + len(cells), output, info=info, repl=True, force=True)

    if not root:
        while True:
            line = comm.bcast('', root = 0)
            if not line: return
            execute_line(line)

    saturn_dir = os.path.expanduser('~/.saturn')
    os.makedirs(saturn_dir, exist_ok=True)

    try:
        g = {}  # fake empty globals;
                # not specifying any get_globals throws an exception inside repl.run();
                # specifying nb.globals breaks checkpointing inside repl; not sure why
        repl = PythonReplWithExecute(
            execute = execute_line,
            get_globals=lambda: g,
            get_locals=lambda: nb.l,
            vi_mode=False,
            history_filename=saturn_dir + '/history',
            startup_paths=None,
            debug=debug,
        )
    except Exception as e:
        print("Caught exception setting up REPL:", e)
        raise

    # Add the code cells to history
    for cell in nb.cells:
        for line in cell.repl_history():
            repl.history.append_string(line)

    result = True

    @repl.add_key_binding('c-q')
    def _(event):
        nonlocal result
        event.app.exit(exception=EOFError)
        result = False

    # TODO: think about changing this to a toggle
    @repl.add_key_binding('f10')
    def _(event):
        nonlocal result
        nb.dry_run = True
        event.app.exit(exception=EOFError)
        result = False

    @repl.add_key_binding('c-w')
    def _(event):
        global skip_repl
        skip_repl = True
        event.app.exit(exception=EOFError)

    try:
        repl.run()
    except Exception as e:
        print("Caught exception in REPL:", e)
        raise

    if using_mpi:
        comm.bcast('', root = 0)

    return result

@argh.arg('infn', help="input notebook")
@argh.arg('outfn', nargs='?', help="output notebook (if empty, input modified in place)")
@argh.arg('--strip-output', help="also strip all output")
def clean(infn,
          outfn,
          strip_output = False):
    """Remove all binary data from the notebook."""
    if not outfn:
        outfn = infn

    if os.path.exists(infn):
        with atomic_write(outfn, mode='w', overwrite=True) as of:
            with open(infn) as f:
                pf = peekable(f)
                for line in pf:
                    marker_line = line.lstrip(' \t')
                    if marker_line.startswith('#saturn>') and c.SaturnCell._external_prefix in marker_line:
                        continue
                    if strip_output and marker_line.startswith('#o>'): continue
                    if marker_line.startswith('#o> png'): continue
                    if marker_line.startswith('#chk>') and marker_line.strip() != '#chk>':
                        of.write(line[:len(line) - len(marker_line)] + '#chk>\n')
                        while pf and pf.peek().lstrip(' \t').startswith('#chk>'):
                            next(pf)
                        continue
                    if marker_line.startswith('#var>'):
                        # Keep the first line, but skip all subsequent lines
                        while pf and pf.peek().lstrip(' \t').startswith('#var>'):
                            next(pf)
                    of.write(line)

@argh.arg('infn', help="input notebook")
@argh.arg('i',   nargs='?', type=int, help="image index")
@argh.arg('out', nargs='?', help="output PNG filename")
@argh.arg('--external', help="external zip archive with binary content")
def image(infn, i, out,
          external = '',
          ):
    """Extract an image from the notebook."""
    if i is not None and not out:
        console.print("Must specify output filename, if image is specified")
        return

    with open(infn) as f:
        cells = c.parse(f, external, show_only = True, info=info, external_base=os.path.dirname(infn))

    count = 0
    for cell in cells:
        if not isinstance(cell, c.OutputCell): continue

        for x in cell.composite_:
            if not isinstance(x, bytes): continue

            if i is None:
                print(f"{count}:")
                show_png(x)
            elif i == count:
                with open(out, 'wb') as f:
                    f.write(x)

            count += 1

def version():
    """Show version of Saturn and its dependencies."""
    from importlib_metadata import version as ver
    console.print(f"Saturn [version]{ver('saturn_notebook')}[/version] (Python {sys.version})")
    for dep in ['wurlitzer', 'rich', 'ptpython',
                'dill', 'markdown', 'atomicwrites',
                'pygments', 'more_itertools', 'matplotlib', 'nbformat', 'pywebview']:
        try:
            console.print(f"   {dep} [version]{ver(dep)}[/version]")
        except Exception:
            console.print(f"   {dep} [error]not found[/error]")
    if has_viewer:
        console.print(f"Config path: [path]{viewer.config_path}[/path]")

@argh.arg('infn', help="Jupyter notebook")
@argh.arg('outfn', nargs='?', help="output notebook (if empty, show the cells instead)")
@argh.arg('-g', '--gui', help="view notebook in GUI")
@argh.arg('--version', help="notebook version")
@argh.arg('--external', help="external zip archive with binary content")
@argh.arg('--inline', help="embed binary content inline instead of using an external archive")
@argh.arg('--force-external', help="replace an existing external archive even if it has no matching Saturn manifest")
@argh.arg('--html', help="save HTML to a file")
@argh.arg('-k', '--katex', help="include KaTeX in HTML output")
@argh.arg('--standalone', help="inline CSS instead of linking CDN assets in HTML output")
@argh.arg('--debug', help="show debugging information")
def convert(infn,
            outfn,
            gui = False,
            version = 4,
            external = '',
            inline = False,
            force_external = False,
            html = '',
            katex = False,
            standalone = False,
            debug = False):
    """Convert a Jupyter notebook into a Saturn notebook."""
    import nbformat
    jnb = nbformat.read(infn, as_version=version)
    cells = jupyter_convert.from_jupyter(jnb, info)

    if not outfn:
        if gui:
            require_viewer()
            html = io.StringIO()
        _show(cells, html, katex, standalone, debug)
        if gui:
            viewer.view(html.getvalue())
    else:
        nb = notebook.Notebook(name = outfn)
        nb.add(cells)
        nb.move_all_incoming()
        nb.save(outfn, save_external_name(outfn, external, inline), inline=inline, force_external=force_external)


@argh.arg('infn', help="input notebook")
@argh.arg('outfn', nargs='?', help="output notebook (if empty, input modified in place)")
@argh.arg('--external', help="external zip archive with binary content")
@argh.arg('--inline', help="embed binary content inline instead of using an external archive")
@argh.arg('--force-external', help="replace an existing external archive even if it has no matching Saturn manifest")
def rehash(infn,
           outfn,
           external = '',
           inline = False,
           force_external = False):
    """Rehash all the code cells, updating the hashes stored with checkpoints and variable cells. (advanced)"""
    if not outfn:
        outfn = infn

    with open(infn) as f:
        cells = c.parse(f, external, info=info, external_base=os.path.dirname(infn))

    nb = notebook.Notebook(name = infn)
    nb.add(cells)
    nb.rehash()

    nb.save(outfn, save_external_name(outfn, external, inline), inline=inline, force_external=force_external)

@argh.arg('infn', help="input notebook")
@argh.arg('external', help="external zip archive with binary content")
@argh.arg('outfn', nargs='?', help="output notebook (if empty, input modified in place)")
@argh.arg('--force-external', help="replace an existing external archive even if it has no matching Saturn manifest")
def extract(infn,
            external,
            outfn,
            force_external = False):
    """Extract embedded binary content into external zip archive."""
    if not outfn:
        outfn = infn

    with open(infn) as f:
        cells = c.parse(f, '', info=info, external_base=os.path.dirname(infn))       # read without external

    nb = notebook.Notebook(name = infn)
    nb.add(cells)
    nb.move_all_incoming()

    nb.save(outfn, save_external_name(outfn, external, inline=False), force_external=force_external)

@argh.arg('infn', help="input notebook")
@argh.arg('external', help="external zip archive with binary content")
@argh.arg('outfn', nargs='?', help="output notebook (if empty, input modified in place)")
def embed(infn,
          external,
          outfn):
    """Embed binary content from external zip archive into notebook body."""
    if not outfn:
        outfn = infn

    with open(infn) as f:
        cells = c.parse(f, external, info=info, external_base=os.path.dirname(infn))

    nb = notebook.Notebook(name = infn)
    nb.add(cells)
    nb.move_all_incoming()

    nb.save(outfn, '', inline=True)      # write without external

@argh.arg('-c', '--clean', help="run from scratch, ignoring checkpoints")
@argh.arg('-a', '--auto-capture', help="automatically capture images")
@argh.arg('-e', '--external', help="external zip archive with binary content")
@argh.arg('--inline', help="embed binary content inline instead of using an external archive")
@argh.arg('--force-external', help="replace an existing external archive even if it has no matching Saturn manifest")
@argh.arg('--debug', help="show debugging information")
@argh.arg('--no-mpi', help="disable MPI awareness")
@argh.arg('-n', '--dry-run', help="don't save the processed notebook")
@argh.arg('--only-root-output', help="suppress output everywhere but rank 0 (for MPI)")
def _run(clean = False,
        auto_capture = False,
        external = '',
        inline = False,
        force_external = False,
        debug = False,
        no_mpi = False,
        dry_run = False,
        only_root_output = False):
    """Launch Saturn REPL."""
    run('', '', clean, auto_capture, external, inline, force_external, debug, no_mpi, dry_run, only_root_output, True)

def main():
    global argv

    parser = argh.ArghParser()
    parser.set_default_command(_run)

    if '--' in sys.argv:
        idx = sys.argv.index('--')
        argv = sys.argv[idx+1:]
        sys.argv = sys.argv[:idx]
    commands = [show, run, clean, image, version, convert, rehash, extract, embed]
    parser.add_commands(commands)
    parser.dispatch()

if __name__ == '__main__':
    main()
