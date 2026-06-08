#!/bin/sh
set -eu

uv run pytest
uv run ruff check .
uv run mypy
uv build
