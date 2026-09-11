"""File templates written into target repositories.

The verify file must stay self-contained bash: CI runs it directly, without
awecontrib installed. The junk pattern below is duplicated in hygiene.py on
purpose — the template may not depend on the package.
"""

JUNK_RE = r"(\.egg-info/|__pycache__/|\.pytest_cache/|\.DS_Store$|\.pyc$|^node_modules/)"

GITIGNORE_PYTHON = [
    "__pycache__/",
    "*.pyc",
    "*.egg-info/",
    ".pytest_cache/",
    ".DS_Store",
    ".venv/",
]

GITIGNORE_NODE = [
    "node_modules/",
    ".DS_Store",
]

_VERIFY_HEADER = """#!/usr/bin/env bash
# One entry point for all checks. CI runs exactly this file.
# Written by awecontrib install; safe to edit by hand.
set -e
cd "$(dirname "$0")"

# Prefer the repo venv when present; CI installs deps into a system python.
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then PY="python3"
else PY="python"
fi
"""

_VERIFY_HYGIENE = """
# hygiene: tracked junk files fail the build
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "verify: not a git repository"; exit 1; }
JUNK_RE='"""
_VERIFY_HYGIENE_TAIL = """'
TRACKED_JUNK="$(git ls-files | grep -E "$JUNK_RE" || true)"
if [ -n "$TRACKED_JUNK" ]; then
  echo "tracked junk files:"
  echo "$TRACKED_JUNK"
  exit 1
fi
"""


def verify_python(include_ruff: bool) -> str:
    parts = [_VERIFY_HEADER]
    if include_ruff:
        parts.append('"$PY" -m ruff check .\n')
    parts.append('"$PY" -m pytest\n')
    parts.append(_VERIFY_HYGIENE + JUNK_RE + _VERIFY_HYGIENE_TAIL)
    return "".join(parts)


_CI_PYTHON = """name: CI

on:
  push:
  pull_request:

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install {install_spec}
      - run: ./verify
"""


def ci_python(install_spec: str) -> str:
    return _CI_PYTHON.format(install_spec=install_spec)


_CI_NODE = """name: CI

on:
  push:
  pull_request:

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
{extra_steps}      - run: {install_cmd}
      - run: {run_cmd}
"""


def ci_node(pm: str, has_package_lock: bool) -> str:
    if pm == "pnpm":
        extra_steps = "      - run: npm install -g pnpm\n"
        install_cmd = "pnpm install --frozen-lockfile"
    elif pm == "yarn":
        extra_steps = ""
        install_cmd = "yarn install --frozen-lockfile"
    else:
        extra_steps = ""
        install_cmd = "npm ci" if has_package_lock else "npm install"
    return _CI_NODE.format(
        extra_steps=extra_steps,
        install_cmd=install_cmd,
        run_cmd="%s run verify" % pm,
    )
