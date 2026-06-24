# Saturn

[Screenshots](#screenshots)

## Features

* Plain-text format. Notebooks are regular Python files. Different types of
  cells are comments with special formatting. Markdown rendering and syntax
  highlighting in the terminal thanks to [rich](https://github.com/Textualize/rich).

* Checkpoints. Special checkpoint cells allow to save the state of the session
  or individual variables.

* Terminal graphics support. When using
  [kitty](https://sw.kovidgoyal.net/kitty/) terminal (or in principle anything
  that supports its [graphics protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol.html))
  matplotlib figures are rendered inline in the terminal.

* MPI awareness. When running under MPI, only rank 0 will write out the
  modified notebook. The REPL will take input on rank 0 and broadcast to other
  ranks. It's also possible to suppress output from all ranks other than 0.

* Ability to convert from Jupyter to Saturn notebooks. This also allows to view
  Jupyter notebooks in the terminal.

## Installation

```
pip install saturn-notebook
```
or add `[viewer]` extras for the `--gui` options below.
```
pip install saturn-notebook[viewer]
```
MPI support is optional and requires an MPI implementation with development
headers available before installing `mpi4py`.
```
pip install saturn-notebook[mpi]
```
Extras can be combined when needed.
```
pip install saturn-notebook[viewer,mpi]
```

## Commands and options

* `saturn show notebook.py`

  Display the notebook in the terminal. No computation is performed. Optional
  `--html OUTPUT.html` flag will produce HTML output. Use `-k, --katex` flag to
  embed [KaTeX](https://katex.org/) headers into non-standalone HTML. Use
  `--standalone` to inline Saturn's CSS instead of linking CDN stylesheets; with
  `--katex`, standalone output embeds bundled KaTeX assets when markdown cells
  contain math delimiters.

  `saturn show notebook.py --html notebook.html -k`

  When installed with `[viewer]` extras, `-g, --gui` option will display the notebook in a GUI (using [pywebview](https://pywebview.flowrl.com/)).

  `saturn show -g notebook.py`

* `saturn run [notebook.py [output.py]]`

  Execute a Python notebook, either modifying it in place, or saving the result
  into a new notebook `output.py`. If no input `notebook.py` is provided, drop
  into REPL (`-i` is implied). When leaving, the REPL will ask whether to save
  the resulting notebook.

  * `-c, --clean`: run from scratch, ignoring the checkpoints.
  * `-a, --auto-capture`: automatically capture matplotlib figures, without `show()`.
  * `-i`, `--interactive`:
    drop into REPL (using [ptpython](https://github.com/prompt-toolkit/ptpython))
    after all the cells are processed; the results of the REPL interaction will
    be added to the notebook.
  * `--no-mpi`: disable MPI awareness.
  * `-n, --dry-run`: don't save the result.
  * `--only-root-output`: under MPI, suppress output from all ranks other than 0.
  * `-e`, `--external notebook.zip`: use external zip archive `notebook.zip`
    to store binary content. If omitted, Saturn stores binary content next to
    the output notebook in `notebook.zip` by default.
  * `--force-external`: replace an existing external archive even if it has no
    matching Saturn manifest.
  * `--inline`: embed binary content directly in the notebook instead of using
    an external archive.

  Any arguments passed after `--` will be passed as `sys.argv` to the notebook.

  `saturn run notebook.py -- arguments --to notebook`

* `saturn clean notebook.py [output.py]`

  Remove generated binary data, checkpoints, variable caches, and external
  archive metadata from the notebook. Use `--strip-output` to remove text output
  lines as well.

* `saturn image notebook.py [i out.png]`

  Save `i`-th image from `notebook.py` into `out.png`. If the last two
  arguments are omitted, show all the images in the notebook together with
  their indices.

* `saturn version`

  Show version of saturn and its dependencies.

* `saturn convert notebook.ipynb [notebook.py]`

  Convert a Jupyter notebook into a Saturn notebook. If the output name
  `notebook.py` is missing, only show the Jupyter notebook. Optional
  `--html OUTPUT.html` flag will produce HTML output. Use `--standalone` to
  inline Saturn's CSS instead of linking CDN stylesheets. With `--katex`,
  standalone output embeds bundled KaTeX assets when markdown cells contain math
  delimiters.
  When writing a Saturn notebook, binary content is stored in an external zip
  archive by default; use `--inline` to embed it directly in the notebook.
  Use `--force-external` to intentionally replace an existing archive without a
  matching Saturn manifest.

  When installed with `[viewer]` extras, `-g, --gui` option will display the notebook in a GUI (using [pywebview](https://pywebview.flowrl.com/)).

* `saturn rehash notebook.py [output.py]`

  Refresh checkpoint and variable-cache hashes without executing the notebook.
  This is useful after mechanical notebook text transformations when the cached
  payloads are still semantically valid. Binary content follows the same
  external archive behavior as `run` and `convert`; use `--inline` for a
  self-contained notebook or `--force-external` to intentionally replace an
  existing archive without a matching Saturn manifest.

* `saturn extract notebook.py notebook.zip`

  Extract inline binary content into external archive.

* `saturn embed notebook.py notebook.zip`

  Embed binary content from external archive into the notebook.


## Cell types

* Markdown cells, prefix `#m>`

  ```
  #m> # Sample notebook
  #m>
  #m> Description using markdown **formatting**.
  ```

* Output cells `#o>`

  There is not usually a reason to modify these by hand, they are filled by
  Saturn with the output of code cells. Text output is stored directly in the
  notebook. Binary output is stored in the external archive by default and the
  notebook keeps a compact reference to the archive member.

  ```
  #saturn> external=notebook.zip
  #o> png name=0123456789abcdef.png
  ```

  Use `--inline` to embed PNG output directly in the notebook instead. Inline
  PNG content is base64-encoded and wrapped in `{{{` and `}}}` markers to allow
  automatic folding.

  ```
  #o> png{{{
  #o> pngiVBORw0KGgoAAAANSUhEUgAAA8AAAAHgCAYAAABq5QSEAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAP
  ...
  #o> pngGAAAgBQEMAAAACkIYAAAAFL4v5JTyvRQ4v1eAAAAAElFTkSuQmCC
  #o> png}}}
  ```

* Checkpoint cells `#chk>`

  These indicate locations, where the code should checkpoint. Checkpointing
  serializes the session and the hash of the previous code blocks. The
  checkpoint is valid if the prior code blocks haven't changed. By default
  Saturn stores the checkpoint payload in the external archive and keeps a
  compact reference in the notebook. Saturn resumes from the last valid
  checkpoint.

  ```
  #saturn> external=notebook.zip
  #chk> name=0123456789abcdef.chk
  ```

  Use `--inline` to embed checkpoint data directly in the notebook. Inline
  checkpoint content is base64-encoded and uses the same folding markers
  (`{{{` and `}}}`).

  ```
  #chk>{{{
  #chk>gANDIJZCQePiVH9SX7wVtBfgrDpcgWu5HUFFiFEeyNF9sVjFcQB9cQEoWAwAAABfX2J1aWx0aW5zX19x
  ...
  #chk>wAyP55wdmz+qIkdBjBrYP3EjdHEkYnWGcSUu
  #chk>}}}
  ```

* Variable cells `#var> x,y,z`

  These cells save only the value of the specified variables (which is useful
  if the full checkpoint is too big). If all the previous code cells haven't
  changed, the cell's saved content is loaded into the specified variables and
  the previous code cell is not evaluated.

* Break cells `#---#`

  These are used to break code cells that don't have any other type of a cell
  between them.

* REPL cells `#-REPL-#`

  These instruct Saturn to drop into an interactive REPL loop, just like the
  `-i` option. All the cells from the REPL will be inserted after this cell in
  the notebook. Afterwards, execution proceeds as normal.

* Code cells

  All contiguous lines, not marked as one of the above, are grouped together
  into code cells.

* Non-skippable code cells `#no-skip#`

  Adding this line anywhere within the code cell will indicate that it
  shouldn't be skipped, even if we are restarting from a checkpoint. This is
  useful, for example, if a cell is modifying `sys.path`, which won't be
  captured in a checkpoint.

* Non-hashable code cells `#no-hash#`

  Adding this line anywhere within the code cell will indicate that it
  shouldn't be hashed, meaning that changing this cell (or removing it
  entirely) won't invalidate the checkpoints below. This should be used only
  with cells that don't change any variables, e.g., purely output or plotting
  cells.

* Saturn cells `#saturn> external=out.zip`

  These provide metadata. For now, the only option is to provide the name of
  the external zip archive to store the binary content.

## Vim support

External archives are the default, so generated notebooks usually contain only
short `name=...` references to binary content. If you use `--inline` or open an
older inline notebook, the binary (non-human-readable) cell content is wrapped
in `{{{`, `}}}` markers. Adding the following comment to the notebook ensures
that Vim starts with inline binary content folded away.

```
# vim: foldmethod=marker foldlevel=0
```

It's also helpful to have Vim recognize the `#m>` prefix to correctly re-format
markdown cells with the `gq` command. This can be done, for example, by adding
the following to `~/.vim/after/ftplugin/python.vim`:

```
setlocal comments=b:#,fb:-,b:#m>
```

## REPL

REPL supports the following keyboard shortcuts:

* `Ctrl-d`: exits the REPL.
* `Ctrl-k`: inserts a checkpoint cell. Equivalent to typing in `#chk>` manually.
* `Ctrl-w`: exits the REPL and doesn't drop into REPL, even if there are more
  REPL cells or `-i` is provided on the command line.
* `Ctrl-q`: exits the REPL and terminates execution of the entire notebook.
* `F10`: aborts execution of the entire notebook and doesn't save it out, even if we are not in `--dry-run` mode.

## Documentation

- [Saturn notebook format](docs/format.md)
- [Execution error policy](docs/error-policy.md)
- [CLI reference](docs/cli.md)
- [External archive lifecycle](docs/archive-lifecycle.md)
- [Release validation](docs/release.md)
- [Workflow examples](docs/examples.md)
- [Third-party notices](docs/third-party.md)

## Development

Install development dependencies and run checks with [uv](https://docs.astral.sh/uv/):

```
uv sync --group dev
uv run pytest
uv run ruff check .
```

`uv run pytest` includes the legacy golden-file notebook regression coverage.
The legacy shell entry point delegates to the same pytest coverage:

```
./tests/run.sh
```

## Screenshots

Running [samples/simple.py](https://github.com/mrzv/saturn/blob/master/samples/simple.py):

* First run performs full computation and saves the checkpoint, as well as the figure output.

![First run](https://github.com/mrzv/saturn/raw/master/resources/screenshots/simple-first-run.png)

* Second run resumes from the checkpoint, since no code before it has changed.

![Second run](https://github.com/mrzv/saturn/raw/master/resources/screenshots/simple-second-run.png)

* Vim shows compact external archive references instead of inline binary
  payloads by default.

![Vim external references](https://github.com/mrzv/saturn/raw/master/resources/screenshots/simple-vim.png)
