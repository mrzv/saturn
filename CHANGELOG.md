# Changelog

## Unreleased

## [1.3.0] - 2025-12-16

### Added

 - `saturn show --gui` shows notebook in a GUI (via [pywebview](https://pywebview.flowrl.com)).
 - `saturn convert --gui` shows Jupyter notebook in a GUI.

### Fixed

 - Make `_` return the last evaluation result in the REPL,
   to match [Python's behavior](https://docs.python.org/3/reference/lexical_analysis.html#reserved-classes-of-identifiers). (Fixes #3.)


## [1.2.2] - 2023-07-05

### Added

 - `saturn version` outputs Python version.
 - `saturn` by itself launches REPL (equivalent to `saturn run -i`)
 - `saturn [run] --no-mpi` disables MPI awareness (useful on login nodes, where
   [importing](importing) mpi4py triggers an error).

### Changed

 - Display blanks in the console, to better preserve the formatting.

### Fixed

 - Notebook directory is added to `sys.path` to make imports work correctly,
   i.e., like in the normal Python run.

## [1.2.1] - 2023-03-24

### Fixed

- Bump ptpython to 3.0.23 to make it run with Python 3.10.


## [1.2.0] - 2023-02-04

### Added

- REPL cells `#-REPL-#`.
- More keyboard shortcuts in REPL:
  - `Ctrl-w`: to exit REPL, but continue execution.
  - `Ctrl-q`: to exit REPL and stop execution of the rest of the notebook.
  - `F10`: aborts execution of the entire notebook and doesn't save it out,
    even if we are not in `--dry-run` mode.
- `saturn run` launches REPL directly.
- If no filename given, ask where to save the notebook when exiting REPL.
- Add ability to inline the name of external archive: `#saturn> external=out.zip`

### Removed

- Remove `Ctrl-w` keyboard shortcut in REPL. (It would save the notebook, which
  seems to be an unnecessary, since it happens at exit.)

## [1.1.0] and before - 2022-12-11

- Plaintext format.
- Checkpoints.
- Terminal graphics in Kitty. Automatically capture matplotlib output.
- MPI awareness.
- Ability to convert from Jupyter.
- Store binary information either inline, or in an external zip archive.
- Export notebooks as HTML.
