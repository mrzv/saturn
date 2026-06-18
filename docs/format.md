# Saturn Notebook Format

Saturn notebooks are regular Python files. Python code remains executable as plain Python, and notebook metadata is stored in comments with reserved prefixes.

## Cell Prefixes

- Code cell: any unprefixed Python source.
- Markdown cell: `#m>` followed by Markdown text.
- Output cell: `#o> ` followed by captured text or image metadata.
- Checkpoint cell: `#chk>` followed by inline checkpoint data, external checkpoint metadata, or nothing for an empty checkpoint marker.
- Variable cell: `#var>` followed by a Python expression naming variables to cache. Additional `#var>` lines store the cache payload.
- Break cell: `#---#` separates cells without display.
- REPL cell: `#-REPL-#` opens the REPL during execution.
- Saturn metadata cell: `#saturn>` stores notebook-level metadata such as `external=notebook.zip`.

Blank lines are preserved with padding logic so round-tripped notebooks remain readable.

## Code Directives

- `#no-skip#` inside a code cell forces that cell to execute even when resuming from a later checkpoint.
- `#no-hash#` excludes the code cell from the running hash used by checkpoint and variable cache validation.

## Outputs

Text output is stored as `#o> ` lines. Carriage-return progress output is collapsed when saving.

PNG output can be stored inline:

```python
#o> png{{{
#o> pngBASE64_DATA
#o> png}}}
```

PNG output can also be stored in an external zip archive:

```python
#saturn> external=notebook.zip
#o> png name=0123456789abcdef.png
```

Archive member names are generated from content hashes and must be simple filenames. Absolute paths, parent-directory paths, and nested paths are ignored when loading.

Saturn-created external archives include a `.saturn-archive.json` manifest. The manifest identifies the file as a Saturn external archive and records the notebook basename that created it.

## External Archives

By default, commands that save binary content write a sibling archive named after the output notebook, for example `analysis.py` and `analysis.zip`.

When the archive is next to the notebook, Saturn stores only the basename in `#saturn> external=...` so the notebook and zip can be moved together. Explicit archive paths outside the notebook directory are preserved as written.

Use `--inline` to embed binary content directly in the notebook instead of writing an external archive.

When saving to an existing external archive, Saturn refuses to overwrite archives that do not contain a matching Saturn manifest. This protects unrelated zip files that happen to have the default name, such as `analysis.zip` next to `analysis.py`. Use `--force-external` only when intentionally replacing such an archive.

## Checkpoints

A checkpoint stores two `dill` payloads:

- The running hash of hashable code cells before the checkpoint.
- The notebook execution locals at that point.

When running a notebook, Saturn looks for the latest checkpoint whose stored hash matches the current code hash, loads its locals, skips earlier skippable code, and resumes after the checkpoint.

Empty checkpoint cells are valid markers. If checkpoint serialization fails, Saturn reports the failure and continues without saving that checkpoint payload.

## Variable Cells

A variable cell stores two `dill` payloads:

- The running hash of the preceding hashable code.
- The value produced by evaluating the variable expression.

On a later run, if the hash still matches, Saturn loads the cached value and skips the preceding code cell. This is intended for expensive computations whose results can be cached independently of the whole notebook state.

## Compatibility

The text syntax is intended to be stable and readable. Serialized checkpoint and variable payload bytes are implementation details and may vary by Python, `dill`, and dependency versions. Tests should prefer semantic load/execute assertions over byte-for-byte comparisons of serialized payloads.
