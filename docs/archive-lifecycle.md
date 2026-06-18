# External Archive Lifecycle

Saturn stores binary notebook payloads, checkpoint state, and variable-cache state in external zip archives by default. This keeps `.py` notebooks readable while preserving generated binary content.

## Creation

When a command saves binary content and `--inline` is not used, Saturn creates a sibling archive named after the output notebook:

```sh
saturn run analysis.py analysis.out.py
```

This writes `analysis.out.py` and, only if binary/cache content exists, `analysis.out.zip`.

If an explicit relative archive is provided, it is resolved beside the output notebook:

```sh
saturn run analysis.py build/analysis.py --external assets.zip
```

This writes `build/analysis.py` and `build/assets.zip`.

## Metadata

When the archive is next to the notebook, Saturn writes only the archive basename into notebook metadata:

```python
#saturn> external=analysis.out.zip
```

This lets the notebook and archive move together as a pair. If the archive is outside the notebook directory, Saturn preserves the explicit path in the metadata.

Every Saturn-created archive contains `.saturn-archive.json`, which identifies the zip as a Saturn external archive and records the notebook basename that created it. Archives outside the notebook directory also record the original absolute notebook path for stricter overwrite protection; sibling archives omit that path so the notebook and archive can move together.

## Overwrite Safety

Saturn refuses to replace an existing archive unless it contains a matching Saturn manifest. This protects unrelated files such as a hand-created `analysis.zip` that happens to have the default name.

Use `--force-external` only when intentionally replacing an unknown or mismatched archive:

```sh
saturn run analysis.py analysis.py --force-external
```

External archives are written atomically. If serialization fails while writing a new archive, the previous archive remains in place.

## Inline And Conversion

Use `--inline` to embed binary content directly in the notebook:

```sh
saturn run analysis.py analysis.inline.py --inline
```

Move existing inline content into an archive:

```sh
saturn extract analysis.inline.py analysis.zip analysis.py
```

Embed archive content back into a self-contained notebook:

```sh
saturn embed analysis.py analysis.zip analysis.inline.py
```

## Compatibility

Older inline notebooks remain readable. External archive member names must be simple filenames; unsafe names such as absolute paths or `..` paths are ignored when loading. External members larger than 100 MiB are ignored to avoid decompressing unexpectedly large archive payloads.
