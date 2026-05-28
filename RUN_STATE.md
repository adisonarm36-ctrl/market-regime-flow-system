# Run State

## Last Completed Work

Phase 7E: Production Reference Readiness.

The project is safe to continue from the current codebase. CSV remains supported, manual upload remains an Advanced/Fallback workflow, Yahoo/yfinance is historical/cache-based only, and opt-in backtests are research assumptions only.

Config source mode now has an explicit `Use bundled fake/demo reference files` toggle. When enabled, missing local reference paths are mapped at runtime to bundled fake/sample files without editing `config/data_sources.yaml`. Production missing-reference warnings remain visible, and demo reference data is labeled as not suitable for production research.

Before configured Yahoo loading runs, the dashboard now shows a startup checklist covering active source, yfinance availability, configured tickers, cache directory/file status when available, local reference coverage, missing references, demo mode state, manual upload fallback availability, and actionable blockers.

The dashboard now includes an explicit `Run Yahoo historical smoke test` button that uses configured tickers and cache-first behavior, then reports rows loaded, date range, cache status, warnings, and errors. It is labeled as a historical connectivity/cache check only.

The dashboard now reports production reference readiness for configured local files. It checks required columns, fake/sample file usage, missing files, and local Yahoo ticker fields without inventing mappings or classifications.

## Current Test Result

`131 passed, 1 pytest cache warning` on 2026-05-27 with Python 3.14.2.

The warning is the known Windows `.pytest_cache` creation/cleanup issue documented in `TROUBLESHOOTING.md`; it does not affect tracked files or test pass/fail status.

## Next Phase

Recommended next phase is Phase 7F: Final docs and regression tests.

Do not start Phase 7F or later unless explicitly requested.

## Exact Next Prompt

```text
Read AGENTS.md, CODEX_WORKFLOW.md, RUN_STATE.md, PROJECT_STATUS.md, PHASE_PLAN.md, and TROUBLESHOOTING.md first.

Implement only Phase 7F: Final Docs And Regression Tests from FIRST_RUN_USABILITY_PLAN.md.

Goal:
Finalize the first-run usability workflow documentation and lock behavior with tests.

Tasks:
- Keep Phase 7C startup checklist visible before configured loading.
- Keep Phase 7D smoke test historical/cache-only.
- Keep Phase 7E production readiness checks visible and non-inferential.
- Do not call Yahoo in tests.
- Update README, PROJECT_STATUS.md, RUN_STATE.md, PHASE_PLAN.md, and FIRST_RUN_USABILITY_PLAN.md.
- Do not add new product features beyond docs/final tests.
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
- Yahoo smoke test is historical/cache-only and not data completeness validation.
- Production readiness checks must never infer missing mappings or classifications.
- Yahoo historical data is price-only; local reference files remain required for metadata, Thailand universe, DR/DRx mapping, security type, sector/country maps, and local DR quality data.
- Do not invent Yahoo ticker mappings.
