"""Tests for awecontrib install."""

import json
import os
import stat

from click.testing import CliRunner

from awecontrib.cli import main

PYPROJECT_PLAIN = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "demo"
version = "0.1.0"
dependencies = ["click>=8.1"]

[tool.setuptools.packages.find]
where = ["src"]
"""

PYPROJECT_FULL = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "demo"
version = "0.1.0"

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.ruff]
line-length = 100
"""


def _out(result):
    try:
        return result.output + result.stderr
    except (ValueError, AttributeError):
        return result.output


def _run(*args):
    return CliRunner().invoke(main, list(args))


def test_python_minimal(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_PLAIN, ".gitignore": "old\n"})
    monkeypatch.chdir(repo)

    result = _run("install")
    assert result.exit_code == 0, _out(result)
    assert "wrote verify" in _out(result)

    verify = repo / "verify"
    assert verify.is_file()
    assert verify.stat().st_mode & stat.S_IXUSR
    text = verify.read_text()
    assert "ruff" not in text
    assert "pytest" in text
    assert "git ls-files" in text

    ci = (repo / ".github" / "workflows" / "ci.yml").read_text()
    assert "./verify" in ci
    assert "-e . pytest" in ci

    gitignore = (repo / ".gitignore").read_text()
    assert "old" in gitignore
    assert "__pycache__/" in gitignore
    assert "*.egg-info/" in gitignore


def test_python_with_ruff_and_dev_extra(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_FULL})
    monkeypatch.chdir(repo)

    result = _run("install")
    assert result.exit_code == 0, _out(result)

    assert "ruff check ." in (repo / "verify").read_text()
    ci = (repo / ".github" / "workflows" / "ci.yml").read_text()
    assert '-e ".[dev]"' in ci


def test_refuses_overwrite_then_force(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_PLAIN, "verify": "#!/bin/sh\necho mine\n"})
    monkeypatch.chdir(repo)

    result = _run("install")
    assert result.exit_code != 0
    assert "refusing to overwrite" in _out(result)
    assert "verify" in _out(result)
    assert not (repo / ".github" / "workflows" / "ci.yml").exists()
    assert "mine" in (repo / "verify").read_text()

    result = _run("install", "--force")
    assert result.exit_code == 0, _out(result)
    assert "pytest" in (repo / "verify").read_text()


def test_ambiguous_repo_needs_flag(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_PLAIN, "package.json": '{"name": "demo"}'})
    monkeypatch.chdir(repo)

    result = _run("install")
    assert result.exit_code != 0
    assert "--python or --node" in _out(result)

    result = _run("install", "--node")
    assert result.exit_code != 0  # no check scripts yet
    result = _run("install", "--python")
    assert result.exit_code == 0, _out(result)


def test_empty_repo_rejected(make_repo, monkeypatch):
    repo = make_repo()
    monkeypatch.chdir(repo)

    result = _run("install")
    assert result.exit_code != 0
    assert "no pyproject.toml or package.json" in _out(result)


def _node_files(scripts, extra=None):
    pkg = {"name": "demo", "version": "0.1.0", "scripts": scripts}
    files = {"package.json": json.dumps(pkg, indent=2)}
    files.update(extra or {})
    return files


def test_node_pnpm(make_repo, monkeypatch):
    repo = make_repo(
        _node_files({"lint": "biome check .", "test": "vitest run"}, {"pnpm-lock.yaml": ""})
    )
    monkeypatch.chdir(repo)

    result = _run("install")
    assert result.exit_code == 0, _out(result)

    pkg = json.loads((repo / "package.json").read_text())
    assert pkg["scripts"]["verify"] == "biome check . && vitest run"

    ci = (repo / ".github" / "workflows" / "ci.yml").read_text()
    assert "npm install -g pnpm" in ci
    assert "pnpm install --frozen-lockfile" in ci
    assert "pnpm run verify" in ci

    assert "node_modules/" in (repo / ".gitignore").read_text()


def test_node_npm_without_lockfile(make_repo, monkeypatch):
    repo = make_repo(_node_files({"typecheck": "tsc --noEmit", "test": "vitest run"}))
    monkeypatch.chdir(repo)

    result = _run("install")
    assert result.exit_code == 0, _out(result)

    pkg = json.loads((repo / "package.json").read_text())
    assert pkg["scripts"]["verify"] == "tsc --noEmit && vitest run"
    ci = (repo / ".github" / "workflows" / "ci.yml").read_text()
    assert "npm install" in ci
    assert "npm ci" not in ci
    assert "npm run verify" in ci


def test_node_without_check_scripts_rejected(make_repo, monkeypatch):
    repo = make_repo(_node_files({}))
    monkeypatch.chdir(repo)

    result = _run("install")
    assert result.exit_code != 0
    assert "typecheck/lint/test" in _out(result)


def test_node_refuses_existing_verify_script(make_repo, monkeypatch):
    repo = make_repo(_node_files({"test": "vitest run", "verify": "vitest run"}))
    monkeypatch.chdir(repo)

    result = _run("install")
    assert result.exit_code != 0
    assert "scripts.verify" in _out(result)

    result = _run("install", "--force")
    assert result.exit_code == 0, _out(result)


def test_no_ci_keeps_existing_workflow(make_repo, monkeypatch):
    existing_ci = "name: Custom\n\non: [push]\n"
    repo = make_repo(
        {
            "pyproject.toml": PYPROJECT_PLAIN,
            ".github/workflows/ci.yml": existing_ci,
            ".github/workflows/release.yml": "name: Release\n",
        }
    )
    monkeypatch.chdir(repo)

    result = _run("install", "--no-ci")
    assert result.exit_code == 0, _out(result)
    assert "wrote verify" in _out(result)
    assert (repo / "verify").is_file()
    assert (repo / ".github" / "workflows" / "ci.yml").read_text() == existing_ci
    assert (repo / ".github" / "workflows" / "release.yml").read_text() == "name: Release\n"
    assert ".gitignore" in _out(result)


def test_no_ci_still_refuses_existing_verify(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_PLAIN, "verify": "#!/bin/sh\ntrue\n"})
    monkeypatch.chdir(repo)

    result = _run("install", "--no-ci")
    assert result.exit_code != 0
    assert "refusing to overwrite" in _out(result)
