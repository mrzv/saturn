# Workflow Examples

These examples show common Saturn workflows. The matching sample notebooks live in `samples/`.

## Plain Script With A Main Guard

Use a top-level `if __name__ == '__main__':` block when you want a file to work both as a normal Python script and as a Saturn notebook.

```sh
python samples/main-guard.py
saturn run samples/main-guard.py /tmp/main-guard.out.py --no-mpi
```

Saturn expands the guarded body into notebook cells and skips sibling `else` branches. Direct Python execution still behaves normally.

## Checkpoint An Expensive Computation

Use an empty `#chk>` marker after expensive setup. The first run saves state; later runs skip to the checkpoint when preceding code has not changed.

```sh
saturn run samples/checkpoint-cache.py /tmp/checkpoint-cache.first.py --no-mpi
saturn run /tmp/checkpoint-cache.first.py /tmp/checkpoint-cache.second.py --no-mpi
```

By default, the checkpoint payload is stored in `/tmp/checkpoint-cache.first.zip` and referenced from the notebook with portable metadata.

## Share A Self-Contained Notebook

Use `--inline` when a single file is more convenient than a notebook plus zip archive.

```sh
saturn run samples/checkpoint-cache.py /tmp/checkpoint-cache.inline.py --inline --no-mpi
```

Inline notebooks remain compatible with Saturn's checkpoint and variable-cache loading.

## Store Images In An External Archive

Generated PNGs are stored externally by default when a notebook is saved.

```sh
saturn run samples/multiple-images.py /tmp/multiple-images.out.py --no-mpi
saturn image /tmp/multiple-images.out.py
saturn image /tmp/multiple-images.out.py 0 /tmp/figure-0.png
```

Use `saturn embed` to turn the notebook plus archive back into a single file:

```sh
saturn embed /tmp/multiple-images.out.py /tmp/multiple-images.out.zip /tmp/multiple-images.inline.py
```

## Export Standalone HTML With Math

Use `--standalone --katex` to produce an HTML file with inline CSS and bundled KaTeX assets. Saturn only includes the KaTeX payload when math delimiters are present in markdown cells.

```sh
saturn show samples/math-html.py --html /tmp/math.html --standalone --katex
```

Without math, `--standalone --katex` still writes standalone HTML, but omits the KaTeX assets.
