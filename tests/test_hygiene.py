"""Tests for awecontrib hygiene."""

from click.testing import CliRunner

from awecontrib.cli import main


def _out(result):
    try:
        return result.output + result.stderr
    except (ValueError, AttributeError):
        return result.output


def _run(*args):
    return CliRunner().invoke(main, list(args))


def test_clean_repo(make_repo, monkeypatch):
    repo = make_repo({"src/demo/__init__.py": ""})
    monkeypatch.chdir(repo)

    result = _run("hygiene")
    assert result.exit_code == 0, _out(result)
    assert "clean" in _out(result)


def test_junk_detected(make_repo, monkeypatch):
    repo = make_repo(
        {
            "src/demo/__init__.py": "",
            "src/demo.egg-info/PKG-INFO": "",
            "tests/__pycache__/x.pyc": "",
            ".DS_Store": "",
        }
    )
    monkeypatch.chdir(repo)

    result = _run("hygiene")
    assert result.exit_code == 1
    assert "src/demo.egg-info/PKG-INFO" in _out(result)
    assert "tests/__pycache__/x.pyc" in _out(result)
    assert ".DS_Store" in _out(result)


def test_fix_prints_git_rm_command(make_repo, monkeypatch):
    repo = make_repo(
        {
            "src/demo/__init__.py": "",
            "src/demo.egg-info/PKG-INFO": "",
            "tests/__pycache__/x.pyc": "",
            ".DS_Store": "",
        }
    )
    monkeypatch.chdir(repo)

    result = _run("hygiene", "--fix")
    assert result.exit_code == 1
    assert "git rm -r --cached .DS_Store src/demo.egg-info tests/__pycache__" in _out(result)


def test_not_a_git_repo(make_repo, monkeypatch):
    repo = make_repo({"pyproject.toml": "[project]\n"}, git=False)
    monkeypatch.chdir(repo)

    result = _run("hygiene")
    assert result.exit_code != 0
    assert "git ls-files failed" in _out(result)
