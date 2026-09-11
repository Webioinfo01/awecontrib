"""awecontrib CLI entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__, bumper, hygiene, installer


@click.group()
@click.version_option(version=__version__, prog_name="awecontrib")
def main() -> None:
    """Shared tooling for the awe series: one verify entry, one version truth."""


@main.command()
@click.option("--python", "kind", flag_value="python", default=None, help="Treat the repo as a Python project.")
@click.option("--node", "kind", flag_value="node", default=None, help="Treat the repo as a Node project.")
@click.option("--force", is_flag=True, help="Overwrite an existing verify entry or CI file.")
@click.option("--no-ci", is_flag=True, help="Only write the verify entry; keep existing CI untouched.")
def install(kind: str | None, force: bool, no_ci: bool) -> None:
    """Write the verify entry point and CI workflow into the current repo."""
    try:
        report = installer.install(Path.cwd(), kind, force, with_ci=not no_ci)
    except installer.InstallError as exc:
        _fail(exc)
    for line in report:
        click.echo(line)


@main.command()
@click.argument("version")
@click.option("--python", "kind", flag_value="python", default=None, help="Bump the Python version carrier.")
@click.option("--node", "kind", flag_value="node", default=None, help="Bump the Node version carrier.")
@click.option("--note", default=None, help="Changelog entry body for this version.")
def bump(version: str, kind: str | None, note: str | None) -> None:
    """Set VERSION in the one place it lives and prepend the CHANGELOG entry."""
    try:
        report = bumper.bump(Path.cwd(), version, note, kind)
    except bumper.BumpError as exc:
        _fail(exc)
    for line in report:
        click.echo(line)


@main.command(name="hygiene")
@click.option("--fix", is_flag=True, help="Print the git rm command instead of just listing.")
def hygiene_cmd(fix: bool) -> None:
    """Fail if junk files (egg-info, __pycache__, node_modules, ...) are tracked."""
    try:
        junk = hygiene.find_junk(Path.cwd())
    except hygiene.HygieneError as exc:
        _fail(exc)
    if not junk:
        click.echo("clean: no tracked junk files")
        return
    click.echo("tracked junk files:")
    for name in junk:
        click.echo("  " + name)
    if fix:
        click.echo("run:")
        click.echo("  git rm -r --cached %s" % " ".join(hygiene.junk_roots(junk)))
    sys.exit(1)


def _fail(exc: Exception) -> None:
    click.echo("awecontrib: %s" % exc, err=True)
    sys.exit(1)
