#!/bin/sh
set -eu

if [ "$#" -gt 1 ]; then
    echo "Usage: $0 [artifact-output-dir]" >&2
    exit 2
fi

uv run pytest
uv run ruff check .
uv run mypy
uv run python -m compileall -q saturn_notebook

if [ "$#" -eq 1 ]; then
    build_dir=$1
    if [ -e "$build_dir" ]; then
        echo "Artifact output directory already exists: $build_dir" >&2
        exit 2
    fi
    mkdir -p "$build_dir"
else
    build_dir=$(mktemp -d)
fi

uv build --out-dir "$build_dir"
uv run twine check "$build_dir"/*
uv run python scripts/check-wheel.py "$build_dir"/*.whl
