"""Tests for awecontrib bump."""

import json

from click.testing import CliRunner

from awecontrib.cli import main

PYPROJECT_STATIC = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "demo"
version = "0.1.0"
description = "demo"
"""

PYPROJECT_DYNAMIC = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "demo"
dynamic = ["version"]
description = "demo"
"""

CHANGELOG = """# Changelog

## v0.1.0

- first release.
"""


def _out(result):
    try:
        return result.output + result.stderr
    except (ValueError, AttributeError):
        return result.output


def _run(*args):
    return CliRunner().invoke(main, list(args))


def test_static_pyproject(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_STATIC, "docs/CHANGELOG.md": CHANGELOG})
    monkeypatch.chdir(repo)

    result = _run("bump", "0.2.0", "--note", "- second release.")
    assert result.exit_code == 0, _out(result)

    text = (repo / "pyproject.toml").read_text()
    assert 'version = "0.2.0"' in text
    assert 'name = "demo"' in text  # formatting preserved

    log = (repo / "docs" / "CHANGELOG.md").read_text()
    assert log.index("## v0.2.0") < log.index("## v0.1.0")
    assert "- second release." in log


def test_dynamic_version_in_init(make_repo, monkeypatch):
    repo = make_repo(
        {
            "pyproject.toml": PYPROJECT_DYNAMIC,
            "src/demo/__init__.py": '__version__ = "0.1.0"\n',
            "docs/CHANGELOG.md": CHANGELOG,
        }
    )
    monkeypatch.chdir(repo)

    result = _run("bump", "0.2.0")
    assert result.exit_code == 0, _out(result)

    assert '__version__ = "0.2.0"' in (repo / "src" / "demo" / "__init__.py").read_text()
    assert 'version = "0.2.0"' not in (repo / "pyproject.toml").read_text()


def test_node_package_json_creates_changelog(make_repo, monkeypatch):
    repo = make_repo({"package.json": '{"name": "demo", "version": "0.1.0"}\n'})
    monkeypatch.chdir(repo)

    result = _run("bump", "0.2.0", "--note", "- second.")
    assert result.exit_code == 0, _out(result)

    pkg = json.loads((repo / "package.json").read_text())
    assert pkg["version"] == "0.2.0"

    log = (repo / "docs" / "CHANGELOG.md").read_text()
    assert log.startswith("# Changelog\n")
    assert "## v0.2.0" in log
    assert "- second." in log


def test_pending_note_marker(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_STATIC})
    monkeypatch.chdir(repo)

    result = _run("bump", "0.2.0")
    assert result.exit_code == 0, _out(result)
    assert "(changelog entry pending)" in (repo / "docs" / "CHANGELOG.md").read_text()


def test_bad_version_rejected(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_STATIC})
    monkeypatch.chdir(repo)

    result = _run("bump", "0.2")
    assert result.exit_code != 0
    assert "X.Y.Z" in _out(result)


def test_duplicate_changelog_rejected(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_STATIC, "docs/CHANGELOG.md": CHANGELOG})
    monkeypatch.chdir(repo)

    result = _run("bump", "0.1.0", "--note", "- again")
    assert result.exit_code != 0
    assert "already has a v0.1.0 entry" in _out(result)


def test_pre_release_suffix_allowed(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": PYPROJECT_STATIC})
    monkeypatch.chdir(repo)

    result = _run("bump", "0.2.0rc1")
    assert result.exit_code == 0, _out(result)
    assert 'version = "0.2.0rc1"' in (repo / "pyproject.toml").read_text()
