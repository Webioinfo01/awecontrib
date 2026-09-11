<div align="center">
  <h1>awecontrib</h1>
  <p><strong>One verify entry per repo, one version truth per repo — shared tooling for the awe series.</strong></p>
  <p>
    <strong>English</strong> ·
    <a href="./README_cn.md">简体中文</a>
  </p>
  <p>
    <img src="https://img.shields.io/pypi/v/awecontrib?style=flat-square&color=7C3AED" alt="Version">
    <img src="https://img.shields.io/badge/python-%E2%89%A53.9-0EA5E9?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/license-MPL--2.0-22C55E?style=flat-square" alt="License">
  </p>
  <p>
    <img src="https://img.shields.io/badge/status-alpha-c96a3d?style=flat-square" alt="Status">
    <img src="https://img.shields.io/badge/install-pip-22C55E?style=flat-square" alt="pip install">
  </p>
</div>

> `awecontrib install` drops a small `verify` file and a minimal CI into a repo. Local and CI then run the exact same command, so they can never drift apart.

## Why

The awe series grew one repo at a time, and the seams show: some release workflows run `unittest` while development runs `pytest`, one repo has tests but no CI at all, versions live in two different places depending on the repo, and a few repos track `egg-info`/`__pycache__` junk. The fix is not more process — it is one entry point per repo that both you and CI call.

## Install

```bash
pip install awecontrib
```

### Agent skill

The repo ships a companion skill at `resources/skills/awecontrib` so coding agents know when to reach for this CLI:

```bash
aweskill install Webioinfo01/awecontrib
```

## Commands

### `awecontrib install`

Run at the repo root. Detects Python (pyproject.toml) vs Node (package.json); pass `--python` or `--node` when both exist.

- Python repo: writes an executable `verify` (pytest, plus `ruff check .` only if the repo configures ruff), a 6-line `.github/workflows/ci.yml` that just calls `./verify`, and appends junk patterns to `.gitignore`.
- Node repo: composes `scripts.verify` from the typecheck/lint/test scripts that already exist in package.json, writes the CI workflow (npm/pnpm/yarn detected from the lockfile), and appends `.gitignore` entries.

Never overwrites an existing `verify` or CI file without `--force`.

### `awecontrib bump <version>`

Sets the version in the one place it lives — static `version` in pyproject, `__version__` in `src/*/__init__.py` for dynamic versioning, or package.json — and prepends a `## v<version>` entry to `docs/CHANGELOG.md` (body from `--note`). No git commits or tags; your release flow keeps owning those.

### `awecontrib hygiene [--fix]`

Fails if junk files (`egg-info`, `__pycache__`, `.pytest_cache`, `.DS_Store`, `*.pyc`, `node_modules`) are tracked in git. `--fix` prints the exact `git rm -r --cached` command instead of running it.

## The verify file

Self-contained bash — CI does not need awecontrib installed:

```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PY=".venv/bin/python"        # prefer the repo venv; CI falls back to python3
[ -x "$PY" ] || PY="python3"

"$PY" -m pytest

# hygiene: tracked junk files fail the build
JUNK_RE='(\.egg-info/|__pycache__/|\.pytest_cache/|\.DS_Store$|\.pyc$|^node_modules/)'
...
```

Edit it freely; it is yours. If your release workflow still runs `unittest discover`, replace that step with `./verify` so publishing uses the same checks as development.

## Not in v1

Badge rewriting (PyPI/npm badges are already dynamic), git automation, batch repo scanning, monorepo support.

## License

MPL-2.0
