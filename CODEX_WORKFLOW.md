# Codex Workflow

Use this workflow before source edits, reviews, commits, or pushes. Read `AGENTS.md`, `RUN_STATE.md`, `PROJECT_STATUS.md`, `PHASE_PLAN.md`, and `TROUBLESHOOTING.md` first.

## Pre-Flight Checks

Run these before coding work to confirm branch, history, remote, Python, compile status, and tests:

```powershell
cd C:\Users\Administrator\Documents\AI\market-regime-flow-system

git status --short
git branch --show-current
git log --oneline -5 --decorate
git remote -v

.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest

Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
```

If the Administrator path is unavailable in the current Codex sandbox, use the active project workspace path and report the substitution.

## Feature Branch Workflow

Create work on a feature branch unless the user explicitly asks to work on `main`.

```powershell
git status --short
git branch --show-current
git checkout -b <feature-branch-name>
```

Keep changes scoped to the requested phase. Do not edit unrelated files. Do not invent financial data, tickers, prices, mappings, or project status.

## Post-Work Checks

Run these before commit or push after code changes:

```powershell
git status --short
git diff --stat
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git diff --stat
git diff --name-status
```

For documentation-only changes, tests are optional unless source code, config behavior, generated outputs, or test files changed. At minimum, run `git status --short` and inspect the documentation diff.

## Commit And Push

Use a clear commit message and push the branch explicitly:

```powershell
git add .
git commit -m "<clear commit message>"
git push -u origin <branch-name>
```

Before committing, ensure generated temp directories such as `tmp_pytest/` and `.pytest_cache/` are removed unless the user explicitly wants them preserved.
