# Subagents

Subagents are scoped helper roles for the Project Orchestrator. They do not override `AGENTS.md`, `CODEX_WORKFLOW.md`, or `docs/agent/PROJECT_AGENT_RUNBOOK.md`.

## Repo Inspector

Responsibilities:

- Inspect current branch, remotes, recent commits, and working tree state.
- Compare requested branch/task against `main`, `origin/main`, `RUN_STATE.md`, and `PROJECT_STATUS.md`.
- Identify stale branches, already-merged work, unexpected dirty files, and ignored generated artifacts.

Stop conditions:

- Dirty files are present before implementation and are not expected.
- Current branch differs from the requested branch.
- Requested work appears already merged or superseded.
- Git history is ambiguous.

## Data Readiness Auditor

Responsibilities:

- Inspect production data readiness docs, generated candidate CSVs, and review worksheets.
- Summarize candidate files, row counts, status counts, missing fields, fallback/demo values, and review gaps.
- Confirm candidate CSVs remain ignored and uncommitted unless explicitly approved.
- Keep all generated rows as candidates until human review.

Stop conditions:

- Task asks to mark rows `Reviewed` or `Approved` without explicit human instruction.
- Task asks to run `scripts/promote_yahoo_candidates.py --apply`.
- Task asks to modify production reference CSVs.
- A required classification, mapping, or source cannot be verified.

## Test Runner

Responsibilities:

- Run the focused tests requested by the task or runbook.
- Run full tests when required.
- Use `--basetemp=tmp_pytest` for pytest.
- Clean local pytest temp/cache artifacts after tests when appropriate.
- Report exact commands and pass/fail results.

Stop conditions:

- Compile fails.
- Tests fail.
- Test command writes unexpected tracked files.
- Dependency or environment issue prevents meaningful verification.

## UI/UX Reviewer

Responsibilities:

- Review dashboard and report UX changes for readability, empty states, warning visibility, no-advice language, and mobile/narrow layout risk.
- Confirm UI changes use existing data only.
- Confirm warnings and raw evidence remain visible.

Stop conditions:

- UI requires new financial or backtest calculations.
- UI hides demo/sample, stale cache, missing reference, or backtest coverage warnings.
- UI introduces buy/sell recommendation language.
- DR/DRx handling becomes mixed with Thailand domestic breadth.

## Safety Reviewer

Responsibilities:

- Check task scope against autonomy levels and human-approval gates.
- Check for secrets, `.env`, tokens, credentials, cookies, private keys, and destructive commands.
- Check that no financial data or classifications are invented.
- Check that production data and candidate promotion rules are respected.

Stop conditions:

- Any Level 5 gate appears.
- Any destructive Git/file operation is requested without explicit approval.
- Source changes affect strategy, signal, ranking, or backtest calculations without approval.
- Candidate review workflow would promote or overwrite production data.

## Docs Maintainer

Responsibilities:

- Keep `RUN_STATE.md`, `PROJECT_STATUS.md`, `PHASE_PLAN.md`, and workflow docs aligned with actual repo state.
- Preserve concise short prompts in `docs/agent/SHORT_PROMPTS.md`.
- Document known cache/test issues in `TROUBLESHOOTING.md`.
- Avoid claiming unsupported realtime, broker, scraping, API-key, advice, or production-readiness capabilities.

Stop conditions:

- Requested docs update would misrepresent implementation state.
- Requested docs update would imply generated candidates are verified production data.
- Requested docs update would hide known warnings or human-review requirements.
