# Run State

## Last Completed Work

Phase 7B: Demo Reference Bootstrap / Sample Reference Mode.

The project is safe to continue from the current codebase. CSV remains supported, manual upload remains an Advanced/Fallback workflow, Yahoo/yfinance is historical/cache-based only, and opt-in backtests are research assumptions only.

Config source mode now has an explicit `Use bundled fake/demo reference files` toggle. When enabled, missing local reference paths are mapped at runtime to bundled fake/sample files without editing `config/data_sources.yaml`. Production missing-reference warnings remain visible, and demo reference data is labeled as not suitable for production research.

## Current Test Result

`121 passed, 1 pytest cache warning` on 2026-05-27 with Python 3.14.2.

The warning is the known Windows `.pytest_cache` creation/cleanup issue documented in `TROUBLESHOOTING.md`; it does not affect tracked files or test pass/fail status.

## Next Phase

Recommended next phase is Phase 7C: Yahoo-first startup checklist.

Do not start Phase 7C or later unless explicitly requested.

## Exact Next Prompt

```text
Read AGENTS.md, CODEX_WORKFLOW.md, RUN_STATE.md, PROJECT_STATUS.md, PHASE_PLAN.md, and TROUBLESHOOTING.md first.

Implement only Phase 7C: Yahoo-First Startup Checklist from FIRST_RUN_USABILITY_PLAN.md.

Goal:
Show a clear startup checklist in the dashboard before attempting the full pipeline.

Tasks:
- Keep Phase 7B demo reference mode explicit and clearly labeled.
- Do not add the Phase 7D smoke test.
- Do not hide missing production references.
- Keep tests network-free.
- Run the workflow checks from CODEX_WORKFLOW.md.
```

## Handoff Notes

- Read `AGENTS.md` before continuing.
- Read `CODEX_WORKFLOW.md`, `PROJECT_STATUS.md`, `PHASE_PLAN.md`, and `TROUBLESHOOTING.md` before coding.
- Do not add live APIs unless a later explicit phase requires and configures them.
- Do not present fake/demo data as real market data.
- Preserve CSV and manual upload fallback.
- Preserve Yahoo as historical price-only source.
- Keep DR/DRx separate from Thailand domestic breadth.
- Bundled Thailand reference files are fake/demo samples only.
- Demo reference bootstrap mode is fake/sample data for smoke testing only.
- Yahoo historical data is price-only; local reference files remain required for metadata, Thailand universe, DR/DRx mapping, security type, sector/country maps, and local DR quality data.
- Do not invent Yahoo ticker mappings.
