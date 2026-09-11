"""awecontrib bump: set the version in the one place it lives, plus CHANGELOG.

Edits are line-targeted, not full-document rewrites, so comments and
formatting in pyproject.toml survive untouched.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:(?:a|b|rc|post|dev)\d*)?$", re.IGNORECASE)


class BumpError(Exception):
    pass


def bump(repo: Path, version: str, note: str | None, kind: str | None) -> list[str]:
    """Set *version* in the repo's single version carrier and prepend the CHANGELOG entry."""
    if not VERSION_RE.match(version):
        raise BumpError("version must look like X.Y.Z (optional a/b/rc/post/dev suffix)")

    pyproject = repo / "pyproject.toml"
    package = repo / "package.json"
    has_pyproject = pyproject.is_file()
    has_package = package.is_file()

    if kind is None:
        if has_pyproject and has_package:
            raise BumpError("both pyproject.toml and package.json found; pass --python or --node")
        if has_pyproject:
            kind = "python"
        elif has_package:
            kind = "node"
        else:
            raise BumpError("no pyproject.toml or package.json in %s" % repo)
    elif kind == "python" and not has_pyproject:
        raise BumpError("no pyproject.toml in %s" % repo)
    elif kind == "node" and not has_package:
        raise BumpError("no package.json in %s" % repo)

    if kind == "python":
        report = _bump_python(repo, pyproject, version)
    else:
        report = _bump_node(package, version)
    return report + _update_changelog(repo, version, note)


def _bump_python(repo: Path, pyproject: Path, version: str) -> list[str]:
    text = pyproject.read_text()
    if re.search(r'^dynamic\s*=\s*\[[^\]]*"version"', text, re.MULTILINE):
        init = _find_version_init(repo)
        if init is None:
            raise BumpError("dynamic version, but no src/*/__init__.py with __version__ found")
        old = _current_init_version(init)
        init.write_text(
            re.sub(
                r"(__version__\s*=\s*)['\"][^'\"]*['\"]",
                r'\g<1>"%s"' % version,
                init.read_text(),
                count=1,
            )
        )
        return ["%s: __version__ %s -> %s" % (init.relative_to(repo), old or "?", version)]
    new = _set_static_project_version(text, version)
    if new is None:
        raise BumpError('cannot find version = "..." under [project] in pyproject.toml')
    pyproject.write_text(new)
    return ["pyproject.toml: version -> %s" % version]


def _set_static_project_version(text: str, version: str) -> str | None:
    lines = text.splitlines(keepends=True)
    in_project = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            continue
        if in_project and re.match(r"version\s*=\s*['\"]", line):
            lines[i] = 'version = "%s"\n' % version
            return "".join(lines)
    return None


def _find_version_init(repo: Path) -> Path | None:
    src = repo / "src"
    if not src.is_dir():
        return None
    for init in sorted(src.glob("*/__init__.py")):
        if re.search(r"__version__\s*=", init.read_text()):
            return init
    return None


def _current_init_version(init: Path) -> str | None:
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]*)['\"]", init.read_text())
    return match.group(1) if match else None


def _bump_node(package: Path, version: str) -> list[str]:
    data = json.loads(package.read_text())
    old = data.get("version")
    data["version"] = version
    package.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return ["package.json: version %s -> %s" % (old or "?", version)]


def _update_changelog(repo: Path, version: str, note: str | None) -> list[str]:
    path = repo / "docs" / "CHANGELOG.md"
    body = note.strip() if note and note.strip() else "- (changelog entry pending)"
    entry = "## v%s\n\n%s\n" % (version, body)

    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Changelog\n\n" + entry)
        return ["created docs/CHANGELOG.md with v%s" % version]

    text = path.read_text()
    if re.search(r"^## v%s\b" % re.escape(version), text, re.MULTILINE):
        raise BumpError("docs/CHANGELOG.md already has a v%s entry" % version)
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("## "):
            lines.insert(i, entry + "\n")
            path.write_text("".join(lines))
            return ["docs/CHANGELOG.md: added v%s" % version]
    new = text if text.endswith("\n") else text + "\n"
    path.write_text(new + "\n" + entry)
    return ["docs/CHANGELOG.md: added v%s" % version]
