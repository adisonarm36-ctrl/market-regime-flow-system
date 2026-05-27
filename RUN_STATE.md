# Run State

## Last Completed Work

Phase 7C: Yahoo-first Startup Checklist.

The project is safe to continue from the current codebase. CSV remains supported, manual upload remains an Advanced/Fallback workflow, Yahoo/yfinance is historical/cache-based only, and opt-in backtests are research assumptions only.

Config source mode now has an explicit `Use bundled fake/demo reference files` toggle. When enabled, missing local reference paths are mapped at runtime to bundled fake/sample files without editing `config/data_sources.yaml`. Production missing-reference warnings remain visible, and demo reference data is labeled as not suitable for production research.

Before configured Yahoo loading runs, the dashboard now shows a startup checklist covering active source, yfinance availability, configured tickers, cache directory/file status when available, local reference coverage, missing references, demo mode state, manual upload fallback availability, and actionable blockers.

## Current Test Result

`127 passed, 1 pytest cache warning` on 2026-05-27 with Python 3.14.2.

The warning is the known Windows `.pytest_cache` creation/cleanup issue documented in `TROUBLESHOOTING.md`; it does not affect tracked files or test pass/fail status.

## Next Phase

Recommended next phase is Phase 7D: One-click Yahoo historical smoke test.

Do not start Phase 7D or later unless explicitly requested.

## Exact Next Prompt

```text
Read AGENTS.md, CODEX_WORKFLOW.md, RUN_STATE.md, PROJECT_STATUS.md, PHASE_PLAN.md, and TROUBLESHOOTING.md first.

Implement only Phase 7D: One-Click Yahoo Smoke Test from FIRST_RUN_USABILITY_PLAN.md.

Goal:
Add a controlled Yahoo historical smoke test button using configured tickers and cache-first behavior.

Tasks:
- Keep Phase 7C startup checklist visible before configured loading.
- Do not start Phase 7E production readiness.
- Do not call Yahoo in tests.
- Do not present smoke-test success as data completeness or research validity.
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
- Startup checklist helpers must remain network-free.
- Yahoo historical data is price-only; local reference files remain required for metadata, Thailand universe, DR/DRx mapping, security type, sector/country maps, and local DR quality data.
- Do not invent Yahoo ticker mappings.
