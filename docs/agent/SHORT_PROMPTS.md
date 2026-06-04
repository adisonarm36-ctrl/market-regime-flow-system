# Short Prompts

Use these prompts after the repo-native workflow docs are present. Each prompt assumes Codex will read `AGENTS.md` and `docs/agent/PROJECT_AGENT_RUNBOOK.md` first.

## Continue Next Safe Task

```text
Read AGENTS.md and docs/agent/PROJECT_AGENT_RUNBOOK.md. Continue the next safe task from RUN_STATE.md. Follow autonomy rules. Stop on human-approval gates.
```

## Run Only One Named Task

```text
Run task: <TASK_NAME>. Use branch: <BRANCH_NAME>. Follow PROJECT_AGENT_RUNBOOK. Do not continue to the next task.
```

## Inspect Only

```text
Inspect current repo state and recommend next task. Do not edit files.
```

## Production Data Review Only

```text
Summarize generated candidate CSVs. Do not modify CSVs. Do not run --apply.
```

## Preserve Review Worksheet

```text
Preserve data/reference/generated/REVIEW_WORKSHEET.md on the current branch. Do not modify candidate CSVs. Do not run --apply. Commit and push only the worksheet if it is the only intended change.
```

## Update Handoff Docs

```text
Update RUN_STATE.md and PROJECT_STATUS.md for the completed task. Do not modify source code. Do not change generated candidate CSVs.
```

## Dry-Run Candidate Promotion Only

```text
Run Yahoo candidate promotion dry-run only. Do not run --apply. Do not modify CSVs. Summarize validation errors, coverage gaps, and rows still blocked.
```

## Human Review Support

```text
Help review generated Yahoo candidate rows. Do not mark rows Reviewed or Approved. Do not invent classifications. Summarize missing fields, fallback fields, and trusted source types needed for human review.
```
