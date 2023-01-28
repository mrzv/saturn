# Changelog

## Unreleased

### Added

- REPL cells `#-REPL-#`.
- More keyboard shortcuts in REPL:
  - Ctrl-w: to exit REPL, but continue execution.
  - Ctrl-q: to exit REPL and stop execution of the rest of the notebook.
- Make `saturn run` into a command that launches REPL directly.
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
