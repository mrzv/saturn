#!/bin/sh
set -eu

uv run pytest
uv run ruff check .
uv run mypy
uv run python -m compileall -q saturn_notebook
build_dir=$(mktemp -d)
uv build --out-dir "$build_dir"
uv run twine check "$build_dir"/*
uv run python scripts/check-wheel.py "$build_dir"/*.whl
