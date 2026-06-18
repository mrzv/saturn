# Release Validation

Use the release validation script before publishing a Saturn build:

```sh
bash scripts/validate-release.sh
```

For a release, pass the artifact directory and upload those same validated files:

```sh
bash scripts/validate-release.sh dist
```

The script runs the same checks that should protect a release artifact:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy`
- `uv run python -m compileall -q saturn_notebook`
- `uv build --out-dir <artifact directory>`
- `uv run twine check <artifacts>`
- `uv run python scripts/check-wheel.py <built wheel>`

The wheel check verifies required package data, including bundled KaTeX assets and notices, and then installs the wheel into a temporary `uv` virtual environment. The installed `saturn` command is smoke-tested with `--help`, `version`, standalone KaTeX HTML export, and a basic notebook run.

Release checklist:

- Start from a clean worktree except for intentionally ignored local files.
- Update `CHANGELOG.md` under `Unreleased` before cutting a release.
- Optionally run `bash scripts/validate-release.sh` before tagging for confidence.
- Tag the release commit, then run `bash scripts/validate-release.sh dist`.
- Inspect the validated wheel and sdist names in `dist/`, and upload those same files.

Without an argument, the validation script builds into a temporary directory so stale files under `dist/` cannot mask packaging problems. With an artifact directory argument, the directory must not already exist; this prevents uploading stale files alongside the validated build.

## PyPI Release Flow

Saturn uses dynamic versions from git tags through `uv-dynamic-versioning`. The release version comes from a git tag such as `1.4.0`; do not edit `pyproject.toml` to set the version.

1. Decide the version. For user-visible behavior changes, prefer a minor release such as `1.4.0` over a patch release.

2. Finalize `CHANGELOG.md`. Move the current `Unreleased` contents under a dated release heading, for example:

   ```md
   ## [1.4.0] - 2026-06-09
   ```

   Leave a fresh empty `## Unreleased` section above it.

3. Commit the changelog update:

   ```sh
   git add CHANGELOG.md
   git commit -m "Prepare 1.4.0 release"
   ```

4. Optionally run release validation before tagging for confidence:

   ```sh
   bash scripts/validate-release.sh
   ```

5. Create an annotated tag from the release commit:

   ```sh
   git tag -a 1.4.0 -m "Release 1.4.0"
   ```

6. Build and validate the tagged artifacts:

   ```sh
   rm -rf dist
   bash scripts/validate-release.sh dist
   ```

7. Verify the artifact version in the validated `dist/` files:

   ```sh
   ls dist
   ```

   Confirm the filenames contain the exact release version, such as `1.4.0`, and do not contain `.dev`, `.post`, or `+<hash>`.

8. Optionally upload to TestPyPI first:

   ```sh
   uv run twine upload --repository testpypi dist/*
   ```

9. Upload to PyPI:

   ```sh
   uv run twine upload dist/*
   ```

   Use a PyPI API token when prompted, or set credentials in the environment:

   ```sh
   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD=pypi-...
   ```

10. Push the release commit and tag:

    ```sh
    git push origin HEAD:<branch>
    git push origin 1.4.0
    ```

Important cautions:

- PyPI files are immutable. If a bad `1.4.0` is uploaded, another file with the same version cannot replace it.
- Build only from a clean tagged commit.
- If the built filename contains `.dev`, `.post`, or `+<hash>`, stop and fix the tag/version state before uploading.
- If working from a detached `HEAD`, attach or push the release commit to the intended branch before treating it as an official release.
