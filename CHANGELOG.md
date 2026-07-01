# Changelog

## Unreleased

### Changed

 - Kitty graphics support now probes the terminal protocol directly before
   falling back to environment-based detection.

### Fixed

 - Updated the locked `cryptography` dependency to avoid vulnerable bundled
   OpenSSL wheels.

## [1.4.0] - 2026-06-20

### Added

 - `saturn run`, `convert`, and `rehash` now store binary content in a sibling
   external zip archive by default, with `--inline` for self-contained notebooks.
 - Standalone HTML export can embed bundled KaTeX CSS, JavaScript, and fonts when
   `--standalone --katex` is used and markdown cells contain math delimiters.
 - Added KaTeX license and provenance notices for the bundled standalone HTML
   math-rendering assets.
 - Top-level `if __name__ == '__main__':` bodies can be used as notebook content,
   so files can remain directly runnable as Python scripts.
 - Added documentation for CLI behavior, notebook file format, execution error
   policy, external archive lifecycle, release validation, and common workflows.
 - Added pytest, Ruff, mypy, CI, release validation, and subprocess coverage for
   stable CLI workflows, cache reuse, extract/embed, and archive handling.

### Changed

 - Relative external archive paths are resolved beside the output notebook, and
   sibling archives are recorded with portable basename metadata.
 - Existing external archives now require a matching Saturn manifest before they
   are overwritten; `--force-external` intentionally replaces unknown archives.
 - Normal `saturn run` errors now save processed notebook state and then re-raise
   the original exception instead of silently succeeding.
 - In-process notebook runs restore `sys.argv` and `sys.path` after execution.
 - MPI detection, HTML rendering, Jupyter conversion, archive handling, and
    notebook execution state are split into smaller testable units.
 - Supported Python versions now start at Python 3.10 because several patched
   security dependency releases no longer support Python 3.9.

### Fixed

 - External zip archives are written atomically so failed writes do not replace
   an existing archive.
 - Unsafe external archive member names are ignored when loading notebook content.
 - External archive member lookups avoid `zipfile.Path` so cached notebooks load
   correctly on Python 3.9.
 - Empty Saturn metadata and variable cells parse safely.
 - Optional imports, missing `TERM`, and traceback filenames containing colons are
   handled more defensively.

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
