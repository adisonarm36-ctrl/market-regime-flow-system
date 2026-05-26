# Troubleshooting

Common issues already encountered in this project and the expected fixes.

## Git Identity Unknown

Symptom: `git commit` fails because author identity is unknown.

Fix:

```powershell
git config user.name "<name>"
git config user.email "<email>"
```

Use repository-local config unless the user asks for global config.

## Python 3.8 vs 3.11 Type-Hint Issue

Symptom: syntax or import errors from modern type hints such as `list[str]`, `dict[str, Any]`, `X | None`, or newer stdlib typing behavior.

Fix: use the project virtual environment and confirm the intended Python version:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m compileall src
```

If compatibility with Python 3.8 is required, avoid `X | None` and use `Optional[X]`; otherwise keep the project on the virtualenv Python used by CI/local tests.

## Pytest Temp Permission Issue

Symptom: pytest fails or warns when creating temp/cache files.

Fix:

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
```

Use `--basetemp=tmp_pytest` for repeatable temp placement in the project directory.

## Codex CLI Not Found

Symptom: `codex` is not recognized.

Fix: check whether the CLI is installed and whether npm global binaries are on `PATH`.

```powershell
where.exe codex
where.exe codex.cmd
npm prefix -g
```

Use `codex.cmd` on Windows when PowerShell cannot execute the `.ps1` shim.

## Node/npm PATH Issue

Symptom: `node`, `npm`, or installed npm global commands are not recognized.

Fix:

```powershell
where.exe node
where.exe npm
npm prefix -g
```

Add the npm global bin directory to the user `PATH` outside the project when needed.

## PowerShell Blocks npm.ps1 or codex.ps1

Symptom: PowerShell reports that `npm.ps1` or `codex.ps1` cannot be loaded because script execution is disabled.

Fix: use the `.cmd` shim instead:

```powershell
npm.cmd --version
codex.cmd --version
```

Only change execution policy if the user explicitly approves it.

## Old Branch Based Before main

Do not merge old branches that are based before current `main`. First inspect history and either rebase carefully or create a fresh branch from `main` and reapply the needed changes.

```powershell
git branch --show-current
git log --oneline -5 --decorate
git fetch origin
```

## Avoid reset --hard

Do not use `git reset --hard` unless explicitly recovering and changes are backed up. Prefer inspecting status and diffs first:

```powershell
git status --short
git diff --stat
git diff --name-status
```
