# Saturn

[Screenshots](#screenshots)

## Features

* Plain-text format. Notebooks are regular Python files. Different types of
  cells are comments with special formatting.

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

## Commands and options

* `saturn show notebook.py`

  Display the notebook in the terminal. No computation is performed. Optional
  `--html OUTPUT.html` flag will produce HTML output. Use `-k, --katex` flag to
  embed [KaTeX](https://katex.org/) header into the HTML.

  `saturn show notebook.py --html notebook.html -k`

* `saturn run notebook.py [output.py]`

  Execute a Python notebook, either modifying it in place, or saving the result
  into a new notebook `output.py`.

  * `-c, --clean`: run from scratch, ignoring the checkpoints.
  * `-a, --auto-capture`: automatically capture matplotlib figures, without `show()`.
  * `-i`, `--interactive`:
    drop into REPL (using [ptpython](https://github.com/prompt-toolkit/ptpython))
    after all the cells are processed; the results of the REPL interaction will
    be added to the notebook.
  * `-n, --dry-run`: don't save the result.
  * `--only-root-output`: under MPI, suppress output from all ranks other than 0.

  Any arguments passed after `--` will be passed as `sys.argv` to the notebook.

  `saturn run notebook.py -- arguments --to notebook`

* `saturn clean notebook.py [output.py]`

  Remove all binary data from the notebook. Useful for getting rid of large
  checkpoints.

* `saturn image notebook.py [i out.png]`

  Save `i`-th image from `notebook.py` into `out.png`. If the last two
  arguments are omitted, show all the images in the notebook together with
  their indices.

* `saturn version`

  Show version of saturn and its dependencies.

* `saturn convert notebook.ipynb [notebook.py]`

  Convert a Jupyter notebook into a Saturn notebook. If the output name
  `notebook.py` is missing, only show the Jupyter notebook. Optional
  `--html OUTPUT.html` flag will produce HTML output.


## Cell types

* Markdown cells, prefix `#m>`

  ```
  #m> # Sample notebook
  #m>
  #m> Description using markdown **formatting**.
  ```

* Output cells `#o>`

  There is not usually a reason to modify these by hand, they are filled by
  Saturn with the output of code cells. If they contain PNG information, it's
  base64-encoded and wrapped in `{{{` and `}}}` to allow automatic folding.

  ```
  #o> <matplotlib.image.AxesImage object at 0x114217550>
  #o> png{{{
  #o> pngiVBORw0KGgoAAAANSUhEUgAAA8AAAAHgCAYAAABq5QSEAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAP
  ...
  #o> pngGAAAgBQEMAAAACkIYAAAAFL4v5JTyvRQ4v1eAAAAAElFTkSuQmCC
  #o> png}}}
  ```

  In Vim with `foldmethod=marker`:
  ```
  #o> <matplotlib.image.AxesImage object at 0x114217550>
  +--135 lines: o> png--------------------------------------------------
  ```

* Checkpoint cells `#chk>`

  These indicate locations, where the code should checkpoint. Checkpointing
  serializes the session, which is stored base64-encoded in the same cell. The
  cell also stores the hash of the previous code blocks, and the checkpoint is
  valid if the prior code blocks haven't changed. By default saturn will resume
  from the last valid checkpoint. Same folding markers (`{{{` and `}}}`) are used.

  ```
  #chk>{{{
  #chk>gANDIJZCQePiVH9SX7wVtBfgrDpcgWu5HUFFiFEeyNF9sVjFcQB9cQEoWAwAAABfX2J1aWx0aW5zX19x
  ...
  #chk>wAyP55wdmz+qIkdBjBrYP3EjdHEkYnWGcSUu
  #chk>}}}
  ```

  In Vim with `foldmethod=marker`:
  ```
  +-- 36 lines: chk>----------------------------------------------------
  ```

* Variable cells `#var> x,y,z`

  These cells save only the value of the specified variables (which is useful
  if the full checkpoint is too big). If all the previous code cells haven't
  changed, the cell's saved content is loaded into the specified variables and
  the previous code cell is not evaluated.

* Break cells `#---#`

  These are used to break code cells that don't have any other type of a cell
  between them.

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

## Vim support

All the binary (non-human-readable) cell content is wrapped in `{{{`, `}}}`
markers. Adding the following comment to the notebook, ensures that Vim starts
with all the binary content folded away.

```
# vim: foldmethod=marker foldlevel=0
```

It's also helpful to have Vim recognize the `#m>` prefix to correctly re-format
markdown cells with the `gq` command. This can be done, for example, by adding
the following to `~/.vim/after/ftplugin/python.vim`:

```
setlocal comments=b:#,fb:-,b:#m>
```

## Screenshots

Running [samples/simple.py](https://github.com/mrzv/saturn/blob/master/samples/simple.py):

* First run performs full computation and saves the checkpoint, as well as the figure output.

![First run](https://github.com/mrzv/saturn/raw/master/resources/screenshots/simple-first-run.png)

* Second run resumes from the checkpoint, since no code before it has changed.

![Second run](https://github.com/mrzv/saturn/raw/master/resources/screenshots/simple-second-run.png)

* Vim folds the binary content.

![Vim folding](https://github.com/mrzv/saturn/raw/master/resources/screenshots/simple-vim.png)
