# Saturn CLI Reference

This page summarizes the behavior of Saturn's command-line interface. Run commands with `saturn ...` after installation, or with `uv run python saturn.py ...` from a source checkout.

MPI support is optional. Install `saturn-notebook[mpi]` only in environments that
already provide an MPI implementation and development headers for `mpi4py`.

## `saturn show notebook.py`

Display a Saturn notebook without executing code.

- Shows markdown, code, text output, and images already stored in the notebook.
- Resolves relative external archives from the notebook directory.
- Use `--html output.html` to write HTML instead of terminal output.
- Use `--standalone` with `--html` to inline Saturn's CSS instead of linking CDN stylesheets.
- Use `--katex` to render TeX math in markdown cells. Non-standalone HTML links KaTeX from a CDN. Standalone HTML embeds bundled KaTeX assets only when math delimiters are present.
- Use `--gui` when installed with the `viewer` extra to open the notebook in a pywebview window.

Examples:

```sh
saturn show analysis.py
saturn show analysis.py --html analysis.html --standalone --katex
saturn show --gui analysis.py
```

## `saturn run [notebook.py [output.py]]`

Execute a notebook and save the processed notebook state.

- With both input and output paths, Saturn reads `notebook.py` and writes `output.py`.
- With only an input path, Saturn updates that notebook in place.
- With no input path, Saturn starts an interactive REPL and asks where to save on exit.
- Arguments after `--` become `sys.argv` for the notebook.
- Top-level `if __name__ == '__main__':` blocks are treated as notebook content, so scripts can remain directly runnable with Python.
- Normal run errors save processed state before re-raising the original exception. See [Execution error policy](error-policy.md).

Important options:

- `--clean`: ignore existing checkpoint and variable caches and run from scratch.
- `--auto-capture`: capture matplotlib figures without explicit `show()` calls.
- `--interactive`: enter the REPL after processing existing cells.
- `--no-mpi`: disable MPI detection.
- `--dry-run`: execute without saving.
- `--only-root-output`: under MPI, suppress output from non-root ranks.
- `--external notebook.zip`: write binary output, checkpoints, and variable caches to an external archive.
- `--inline`: embed binary content directly in the notebook instead of using an external archive.
- `--force-external`: replace an existing external archive even if it has no matching Saturn manifest.

Examples:

```sh
saturn run analysis.py analysis.out.py --no-mpi
saturn run analysis.py --clean
saturn run analysis.py -- arguments --for notebook
saturn run analysis.py analysis.py --external analysis-assets.zip
saturn run analysis.py analysis.py --external analysis-assets.zip --force-external
saturn run analysis.py self-contained.py --inline
```

## `saturn clean notebook.py [output.py]`

Remove generated outputs, binary payloads, checkpoints, and variable caches.

- Use this before committing a notebook when generated output should not be versioned.
- If `output.py` is omitted, Saturn writes back to `notebook.py`.

Examples:

```sh
saturn clean analysis.py
saturn clean analysis.py analysis.clean.py
```

## `saturn image notebook.py [index output.png]`

List or extract stored PNG output.

- Without an index, Saturn shows all images with their indices.
- With an index and output path, Saturn writes that image to `output.png`.

Examples:

```sh
saturn image analysis.py
saturn image analysis.py 0 figure.png
```

## `saturn convert notebook.ipynb [notebook.py]`

Convert a Jupyter notebook into Saturn format, or display it when no output notebook is provided.

- Markdown, code, text output, and PNG output are converted.
- `--html output.html` writes HTML directly.
- `--standalone` inlines CSS for HTML output.
- `--katex` enables TeX math rendering in markdown cells.
- When writing a Saturn notebook, binary content is externalized by default; use `--inline` for a self-contained notebook.
- Use `--force-external` to intentionally replace an existing archive without a matching Saturn manifest.

Examples:

```sh
saturn convert notebook.ipynb notebook.py
saturn convert notebook.ipynb --html notebook.html --standalone --katex
saturn convert notebook.ipynb notebook.inline.py --inline
```

## `saturn rehash notebook.py [output.py]`

Refresh checkpoint and variable-cache hashes without executing the notebook.

- Use this when notebook text has been transformed but cache payloads remain semantically valid.
- Binary content follows the same external archive behavior as `run` and `convert`.
- Use `--force-external` to intentionally replace an existing archive without a matching Saturn manifest.

Example:

```sh
saturn rehash analysis.py analysis.rehashed.py
```

## `saturn extract notebook.py notebook.zip [output.py]`

Move inline binary content into an external archive.

- Relative archive paths are resolved beside the output notebook.
- The saved notebook stores a portable basename in `#saturn> external=...` when the archive is next to the notebook.
- Existing archives must contain a matching Saturn manifest unless `--force-external` is provided.

Example:

```sh
saturn extract self-contained.py self-contained.zip externalized.py
saturn extract self-contained.py self-contained.zip externalized.py --force-external
```

## `saturn embed notebook.py notebook.zip [output.py]`

Embed external binary content back into the notebook.

- The saved notebook has no `#saturn> external=...` metadata.
- Use this when a single self-contained file is easier to share.

Example:

```sh
saturn embed externalized.py self-contained.zip self-contained.py
```

## `saturn version`

Print Saturn, Python, and key dependency versions.

Example:

```sh
saturn version
```
