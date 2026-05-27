# Run State

## Last Completed Work

Phase 6F: Yahoo-first workflow documentation and final tests.

The project is safe to continue from the current codebase. CSV remains supported, manual upload remains an Advanced/Fallback workflow, Yahoo/yfinance is historical/cache-based only, and opt-in backtests are research assumptions only.

## Current Test Result

`119 passed, 1 pytest cache warning` on 2026-05-27 with Python 3.14.2.

The warning is the known Windows `.pytest_cache` creation/cleanup issue documented in `TROUBLESHOOTING.md`; it does not affect tracked files or test pass/fail status.

## Next Phase

No new feature phase is active.

Recommended next work is production-data readiness:

- replace fake/demo sample reference files with manually verified local files before research use
- verify Thailand universe, security type, liquidity, sector/industry, and DR/DRx mappings
- keep Yahoo as historical OHLCV only, not realtime or metadata source of truth
- add documentation/tests only when behavior changes

## Exact Next Prompt

```text
Read AGENTS.md, CODEX_WORKFLOW.md, RUN_STATE.md, PROJECT_STATUS.md, PHASE_PLAN.md, and TROUBLESHOOTING.md first.

Review production-data readiness for the Yahoo-first research workflow.

Goal:
Identify remaining data-readiness gaps without adding live APIs, scraping, broker integration, realtime data, or financial advice.

Tasks:
- Verify which local reference files are fake/demo samples.
- List required verified replacement files for production research.
- Confirm manual upload fallback remains available.
- Confirm Yahoo remains historical/cache-based only.
- Run tests if source or docs change.
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
- Yahoo historical data is price-only; local reference files remain required for metadata, Thailand universe, DR/DRx mapping, security type, sector/country maps, and local DR quality data.
- Do not invent Yahoo ticker mappings.
