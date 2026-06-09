# Release Validation

Use the release validation script before tagging or publishing a Saturn build:

```sh
bash scripts/validate-release.sh
```

The script runs the same checks that should protect a release artifact:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy`
- `uv run python -m compileall -q saturn_notebook`
- `uv build --out-dir <temporary directory>`
- `uv run twine check <temporary artifacts>`
- `uv run python scripts/check-wheel.py <built wheel>`

The wheel check verifies required package data, including bundled KaTeX assets and notices, and then installs the wheel into a temporary `uv` virtual environment. The installed `saturn` command is smoke-tested with `--help`, `version`, standalone KaTeX HTML export, and a basic notebook run.

Release checklist:

- Start from a clean worktree except for intentionally ignored local files.
- Update `CHANGELOG.md` under `Unreleased` before cutting a release.
- Run `bash scripts/validate-release.sh` locally.
- Inspect the built wheel and sdist names in the validation output.
- Tag from the commit that passed validation.

The validation script builds into a temporary directory so stale files under `dist/` cannot mask packaging problems.
