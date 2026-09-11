"""awecontrib install: write the shared verify entry point and CI into a repo."""

from __future__ import annotations

import json
import stat
from pathlib import Path

from . import templates


class InstallError(Exception):
    pass


def install(repo: Path, kind: str | None, force: bool, with_ci: bool = True) -> list[str]:
    """Install verify + CI into *repo*. Returns a report of what changed."""
    kind = kind or _detect_kind(repo)
    if kind == "python":
        return _install_python(repo, force, with_ci)
    if kind == "node":
        return _install_node(repo, force, with_ci)
    raise InstallError("unknown kind %r (expected --python or --node)" % kind)


def _detect_kind(repo: Path) -> str:
    has_pyproject = (repo / "pyproject.toml").is_file()
    has_package = (repo / "package.json").is_file()
    if has_pyproject and has_package:
        raise InstallError("both pyproject.toml and package.json found; pass --python or --node")
    if has_pyproject:
        return "python"
    if has_package:
        return "node"
    raise InstallError("no pyproject.toml or package.json in %s" % repo)


def _install_python(repo: Path, force: bool, with_ci: bool) -> list[str]:
    verify = repo / "verify"
    ci = repo / ".github" / "workflows" / "ci.yml"
    _guard_existing(repo, [verify] + ([ci] if with_ci else []), force)

    pyproject = (repo / "pyproject.toml").read_text()
    _write_file(verify, templates.verify_python("[tool.ruff]" in pyproject), executable=True)
    report = ["wrote verify (executable)"]

    if with_ci:
        # Reuse the dev extra when it already pulls pytest; otherwise install pytest
        # alongside the package so verify works out of the box.
        install_spec = '-e ".[dev]"' if "pytest" in pyproject else "-e . pytest"
        _write_file(ci, templates.ci_python(install_spec))
        report.append("wrote .github/workflows/ci.yml (pip install %s)" % install_spec)

    added = _append_gitignore(repo, templates.GITIGNORE_PYTHON)
    if added:
        report.append("updated .gitignore (+%d)" % added)
    return report


def _install_node(repo: Path, force: bool, with_ci: bool) -> list[str]:
    pkg_path = repo / "package.json"
    pkg = json.loads(pkg_path.read_text())
    scripts = pkg.setdefault("scripts", {})
    ci = repo / ".github" / "workflows" / "ci.yml"
    _guard_existing(repo, [ci] if with_ci else [], force)
    if "verify" in scripts and not force:
        raise InstallError("refusing to overwrite scripts.verify in package.json; pass --force")

    parts = [name for name in ("typecheck", "lint", "test") if name in scripts]
    if not parts:
        raise InstallError(
            "package.json has none of typecheck/lint/test scripts; add at least one first"
        )
    scripts["verify"] = " && ".join(scripts[name] for name in parts)
    pkg_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n")
    report = ['updated package.json (scripts.verify = "%s")' % scripts["verify"]]

    if with_ci:
        pm = _detect_pm(repo)
        _write_file(ci, templates.ci_node(pm, (repo / "package-lock.json").is_file()))
        report.append("wrote .github/workflows/ci.yml (%s)" % pm)

    added = _append_gitignore(repo, templates.GITIGNORE_NODE)
    if added:
        report.append("updated .gitignore (+%d)" % added)
    return report


def _detect_pm(repo: Path) -> str:
    if (repo / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (repo / "yarn.lock").is_file():
        return "yarn"
    return "npm"


def _guard_existing(repo: Path, paths: list[Path], force: bool) -> None:
    if force:
        return
    existing = [str(p.relative_to(repo)) for p in paths if p.exists()]
    if existing:
        raise InstallError("refusing to overwrite %s; pass --force to replace" % ", ".join(existing))


def _write_file(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _append_gitignore(repo: Path, lines: list[str]) -> int:
    path = repo / ".gitignore"
    existing = set()
    if path.is_file():
        existing = {line.strip() for line in path.read_text().splitlines() if line.strip()}
    missing = [line for line in lines if line not in existing]
    if not missing:
        return 0
    old = path.read_text() if path.is_file() else ""
    new = old if (not old or old.endswith("\n")) else old + "\n"
    path.write_text(new + "\n".join(missing) + "\n")
    return len(missing)
