# Project Agent Runbook

This runbook defines the repo-native workflow for short Codex prompts. Use it with `AGENTS.md`, `CODEX_WORKFLOW.md`, `RUN_STATE.md`, `PROJECT_STATUS.md`, `PHASE_PLAN.md`, and `TROUBLESHOOTING.md`.

The system produces research signals only. It must not create financial advice, buy/sell recommendations, live trading, broker integration, scraping, API-key workflows, realtime feeds, invented market data, or invented reference classifications.

## Project Orchestrator

### Role

The Project Orchestrator owns one safe task at a time.

It must:

- Read `RUN_STATE.md` and `PROJECT_STATUS.md`.
- Determine the next safe task from current status, not from stale branch names.
- Inspect `git status --short` and `git branch --show-current`.
- Run pre-flight checks before implementation.
- Delegate read-only analysis to subagents where useful.
- Implement only one task at a time.
- Run focused tests and full tests appropriate to the task.
- Commit and push the branch if tests pass and the task allows Level 3 autonomy.
- Merge into `main` only when the task risk level allows Level 4 autonomy.
- Update `RUN_STATE.md` and `PROJECT_STATUS.md` after meaningful workflow or project-state changes.
- Stop on conflicts, dirty status, test failures, push errors, ambiguity, or risky data changes.

### Required First Steps

```powershell
git status --short
git branch --show-current
git log --oneline -5 --decorate
git remote -v
```

For source-code tasks, also run:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

For documentation-only tasks, tests are optional under `CODEX_WORKFLOW.md` unless the user explicitly requests them. If tests are skipped, say so in the final response.

### Stop Conditions

Stop and report before editing when:

- `git status --short` shows unexpected dirty files.
- The current branch is not the requested branch and the task depends on branch identity.
- The task requires changing candidate rows to `Reviewed` or `Approved`.
- The task requires `scripts/promote_yahoo_candidates.py --apply`.
- The task requires modifying production reference CSVs.
- The task requires financial, ranking, signal, or backtest calculation changes without explicit approval.
- The task requires deleting files beyond generated temp/cache artifacts.
- The task requires secrets, `.env`, tokens, credentials, cookies, or private keys.
- Tests fail and the failure is not understood.
- Push or merge fails.
- Requirements are ambiguous enough that a safe assumption would risk data integrity.

## Autonomy Levels

### Level 0: Read-Only Inspect

Allowed:

- Read files.
- Inspect Git status, logs, branches, remotes, and ignored files.
- Run read-only validation commands.
- Summarize generated candidate CSVs.
- Recommend next tasks.

Not allowed:

- Editing files.
- Staging, committing, pushing, or merging.
- Changing generated candidate statuses.

### Level 1: Docs-Only Changes

Allowed:

- Edit documentation and workflow files.
- Add review worksheets or runbooks.
- Update `RUN_STATE.md` and `PROJECT_STATUS.md` for accurate handoff.

Guardrails:

- Do not change source code, tests, calculations, config behavior, or production reference data.
- Do not commit generated candidate CSVs automatically.

### Level 2: Safe UI/Test/Code Changes

Allowed:

- Scoped UI, tests, or implementation changes that preserve existing calculations and data semantics.
- Focused tests and full tests.

Guardrails:

- Do not change strategy, signal, ranking, or backtest calculations unless explicitly approved.
- Do not change production reference files unless explicitly approved.

### Level 3: Commit/Push Branch

Allowed:

- Stage only intended files.
- Commit with the requested message or a clear scoped message.
- Push the current branch.

Required:

- `git status --short`
- `git diff --stat`
- `git diff --name-status`
- Appropriate tests or documented reason tests were skipped.

### Level 4: Merge Main After Tests

Allowed only when the user or task explicitly permits merge and the change is low risk.

Required:

- Branch is pushed.
- Working tree is clean.
- Focused and full tests pass.
- Changed files match the task.
- Merge is non-conflicting.
- Full tests pass after merge.
- `main` is pushed.

### Level 5: Human Approval Required

Human approval is required for:

- Running `scripts/promote_yahoo_candidates.py --apply`.
- Changing generated candidate rows to `Reviewed` or `Approved`.
- Modifying production reference CSVs.
- Financial, strategy, ranking, signal, or backtest calculation changes.
- Deleting files beyond generated temp/cache artifacts.
- Database, schema, or migration changes.
- Secrets, `.env`, token, credential, cookie, or private-key changes.
- Force push, `git reset --hard`, or destructive Git operations.

## Subagent Delegation

Use subagents for bounded analysis. Subagents are advisory unless the active prompt grants them a higher autonomy level through the orchestrator.

See `docs/agent/SUBAGENTS.md` for role definitions and stop conditions.

## Production Data Readiness Rules

- Yahoo candidate CSVs under `data/reference/generated/` are generated and ignored by Git.
- Candidate CSV rows start as `NeedsReview`.
- Do not mark rows `Reviewed` or `Approved` without human verification.
- Do not invent ticker mappings, sector classifications, country mappings, security types, asset classes, liquidity, fair values, FX values, or DR mappings.
- `REVIEW_WORKSHEET.md` may be committed if useful for human review.
- `scripts/promote_yahoo_candidates.py` is dry-run by default.
- Never run `scripts/promote_yahoo_candidates.py --apply` without explicit human approval.

## Git And Cache Handling

- `data/cache/` is runtime Yahoo cache and must not be committed.
- `.pytest_cache` and `tmp_pytest/` are local test artifacts and should not be committed.
- The known Windows `.pytest_cache` warning is documented in `TROUBLESHOOTING.md`.
- Generated candidate CSVs are ignored and should not be committed automatically.
- Use `git add -f data/reference/generated/REVIEW_WORKSHEET.md` only when intentionally preserving the worksheet.

## Standard Final Response

Use this structure when work is completed:

```text
Branch used: <branch>
Files changed:
- <path>
Tests run:
- <command>: <result>
Commit hash: <hash or none>
Pushed branch: <branch or none>
Main merged/pushed: <yes/no>
Final git status: <clean or details>
Next short prompts:
- <prompt>
Human-approval gates remaining:
- <gate>
```
