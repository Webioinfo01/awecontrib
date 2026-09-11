<div align="center">
  <h1>awecontrib</h1>
  <p><strong>每个仓库一条 verify 命令、一处版本真相 —— awe 系列的共享工具。</strong></p>
  <p>
    <a href="./README.md">English</a> ·
    <strong>简体中文</strong>
  </p>
  <p>
    <img src="https://img.shields.io/pypi/v/awecontrib?style=flat-square&color=7C3AED" alt="Version">
    <img src="https://img.shields.io/badge/python-%E2%89%A53.9-0EA5E9?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/license-MPL--2.0-22C55E?style=flat-square" alt="License">
  </p>
</div>

> `awecontrib install` 往仓库里放一个 `verify` 文件和一份极简 CI。本地和 CI 从此跑同一条命令，不会再漂移。

## 为什么做

awe 系列是一个仓库一个仓库长出来的，接缝都在：有的 release workflow 跑 `unittest` 而开发时跑的是 `pytest`，有的仓库有测试却没 CI，版本号有的写在 pyproject 有的写在 `__version__`，还有几个仓库把 `egg-info`/`__pycache__` 提交进了 git。解法不是加流程，是每个仓库只留一个入口，你和 CI 都调它。

## 安装

```bash
pip install awecontrib
```

### Agent 技能

仓库自带配套技能 `resources/skills/awecontrib`，告诉 coding agent 什么时候该用这个 CLI：

```bash
aweskill install Webioinfo01/awecontrib
```

## 命令

### `awecontrib install`

在仓库根目录运行。自动识别 Python（pyproject.toml）和 Node（package.json）；两者都在时用 `--python` 或 `--node` 指定。

- Python 仓库：写入可执行的 `verify`（pytest，仓库配了 ruff 才加 `ruff check .`）、一份只调 `./verify` 的 6 行 `.github/workflows/ci.yml`，并向 `.gitignore` 追加垃圾文件模式。
- Node 仓库：用 package.json 里已有的 typecheck/lint/test 脚本拼出 `scripts.verify`，写入 CI workflow（按 lockfile 识别 npm/pnpm/yarn），追加 `.gitignore` 条目。

已存在的 `verify` 或 CI 文件不会覆盖，除非 `--force`。

### `awecontrib bump <版本号>`

只改版本唯一真相那一处——pyproject 静态 `version`、动态版本的 `src/*/__init__.py` 里的 `__version__`、或 package.json——并在 `docs/CHANGELOG.md` 顶部插入 `## v<版本>` 条目（正文用 `--note`）。不做 git 提交和打 tag，那归你的 release 流程管。

### `awecontrib hygiene [--fix]`

git 里跟踪了垃圾文件（`egg-info`、`__pycache__`、`.pytest_cache`、`.DS_Store`、`*.pyc`、`node_modules`）就报错退出。`--fix` 只打印应执行的 `git rm -r --cached` 命令，不替你删。

## verify 文件

自包含 bash，CI 不需要安装 awecontrib：

```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PY=".venv/bin/python"        # 优先用仓库 venv；CI 里回落到 python3
[ -x "$PY" ] || PY="python3"

"$PY" -m pytest

# hygiene: tracked junk files fail the build
JUNK_RE='(\.egg-info/|__pycache__/|\.pytest_cache/|\.DS_Store$|\.pyc$|^node_modules/)'
...
```

随时可以手改，它是你的文件。如果 release workflow 里还在跑 `unittest discover`，把那一步换成 `./verify`，发布就和开发用同一套检查。

## v1 不做

badge 改写（PyPI/npm badge 本来就是动态的）、git 自动化、批量仓库扫描、monorepo 支持。

## 许可

MPL-2.0
