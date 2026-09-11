"""awecontrib hygiene: fail if junk files are tracked in git."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .templates import JUNK_RE

_JUNK_RE = re.compile(JUNK_RE)
_DIR_MARKERS = (".egg-info/", "__pycache__/", ".pytest_cache/", "node_modules/")


class HygieneError(Exception):
    pass


def find_junk(repo: Path) -> list[str]:
    """Return tracked files matching the junk pattern, in git order."""
    proc = subprocess.run(
        ["git", "ls-files"], cwd=repo, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise HygieneError("git ls-files failed (not a git repository?)")
    return [line for line in proc.stdout.splitlines() if _JUNK_RE.search(line)]


def junk_roots(files: list[str]) -> list[str]:
    """Collapse junk files to the directories (or files) to git rm --cached."""
    roots: list[str] = []
    for name in files:
        root = name
        for marker in _DIR_MARKERS:
            idx = name.find(marker)
            if idx != -1:
                root = name[: idx + len(marker)].rstrip("/")
                break
        if root not in roots:
            roots.append(root)
    return roots
