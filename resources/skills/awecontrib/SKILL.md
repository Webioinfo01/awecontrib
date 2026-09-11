---
name: awecontrib
description: "Use when adding or running the shared verify gate in an awe-series repo, wiring CI to call verify, bumping a release version with its CHANGELOG entry, checking git for tracked junk files, or onboarding a new awesome/* repo to shared tooling. 中文触发词：awecontrib、verify 门禁、提交前检查、CI 对齐、统一入口、bump 版本、升版本、垃圾文件、egg-info、__pycache__、新仓库接入。"
---

# awecontrib

One verify entry per repo, one version truth per repo. Use the `awecontrib` CLI directly; do not hand-write `verify` or CI files when the CLI can generate them.

If `awecontrib` is not on PATH: `pip install awecontrib`, or from a local checkout `pip install -e <path>` (the checkout's `.venv/bin/awecontrib` also works).

## Intent Router

| User intent | Command |
|---|---|
| "add verify / CI to this repo", "接入", "对齐" | `awecontrib install` (auto-detects Python/Node; `--python` / `--node` when both exist) |
| "run the checks", "提交前检查" | `./verify` (Python) · `npm run verify` / `pnpm run verify` (Node) |
| "bump to X", "升版本" | `awecontrib bump X [--note "..."]` |
| "junk in git", "egg-info tracked" | `awecontrib hygiene` (`--fix` prints the `git rm --cached` command, never runs it) |
| "release", "tag", "publish", "合并到 main" | **Not awecontrib** — hand off to `$peng-github-release-workflow` |

## Core Rules

1. **Inspect before mutating.** Work on a clean branch. `install` never overwrites an existing `verify` or CI file without `--force`; do not pass `--force` on a repo whose verify has been customized.
2. **verify must pass locally before you commit it.** If it is red, fix the repo, not the gate.
3. **CI runs only verify.** Any check worth running in CI belongs inside verify, so local and CI cannot drift. If a `release.yml` still runs its own test step (for example `unittest discover`), point it at verify.
4. **Tests must pass offline.** A gate that goes red on network hiccups gets ignored. If verify is flaky, find the network call rather than raising timeouts (aweskill's `main()` pinged the npm registry inside tests; the fix was `AWESKILL_NO_UPDATE_CHECK=1` in the vitest config).
5. **One definition per check.** In Node repos prefer `npm run typecheck && npm run test` over inlining `tsc --noEmit && vitest run`, so changing a script changes verify too. Include `build` when the repo has a real build step (bundlers, DTS output).
6. **bump only edits files.** It changes the version carrier (pyproject `version`, `__version__`, or package.json) and prepends `## v<version>` to `docs/CHANGELOG.md`. No commit, no tag — the release flow owns git. Read the CHANGELOG first: some repos keep a standing `## Unreleased` heading that should be renamed, not duplicated.
7. **verify is the repo's file.** Editing it by hand is expected: add a matrix, a build step, a lint step. aweskill keeps its 3 OS × 2 Node matrix because its symlink/junction code is platform-specific; do not collapse it to the template.

## Onboarding a Repo

1. `cd <repo>` on a clean branch (`git status` empty).
2. `awecontrib install` — read what it printed.
3. Run verify locally until green.
4. `awecontrib hygiene` — clean.
5. Commit `verify` (or `package.json`) together with `.github/workflows/ci.yml`.
6. Push; confirm the first CI run is green.
7. If `release.yml` exists, replace its test step with verify.

## Escalation

- verify red because of the repo's own tests or lint → fix the repo; that is the gate doing its job.
- verify red on a fresh checkout but green locally → look for a network or environment dependency in the tests.
- Release, tags, dev → main promotion → `$peng-github-release-workflow`.
- Skill install or projection problems → `$aweskill` / `$aweskill-doctor`.
