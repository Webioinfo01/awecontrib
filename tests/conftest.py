"""Shared fixtures: build throwaway git repos in tmp_path."""

import subprocess
from pathlib import Path

import pytest


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def make_repo(tmp_path):
    def _make(files: dict | None = None, git: bool = True) -> Path:
        repo = tmp_path / "repo"
        repo.mkdir()
        for rel, content in (files or {}).items():
            target = repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        if git:
            _git(repo, "init", "-q")
            _git(repo, "add", "-A")
        return repo

    return _make
