# Phase Plan

Current implementation focus: first-run usability is complete through Phase 7E only.

The Yahoo-first transition is complete through Phase 6F. Phase 7A through 7E first-run usability work is complete. The system supports configured CSV/manual data, optional Yahoo historical OHLCV loading, local reference-driven metadata/universe/mapping workflows, explicit Yahoo cache controls, opt-in research backtests from configured historical prices, missing-yfinance diagnostics, explicit runtime demo reference bootstrap mode, a Yahoo startup checklist before configured loading, an explicit Yahoo historical smoke test, and production reference readiness checks.

## Completed Milestones

- Core data loading, validation, returns, flow proxy, breadth, sector, clustering, momentum, redundancy, and dashboard/report outputs.
- Adapter architecture with CSV/manual upload and Yahoo historical/cache-first adapter.
- Hybrid Yahoo + local reference workflow for metadata, sector/country maps, asset maps, Thailand universes, and DR/DRx mappings.
- Thailand domestic breadth exclusions for DR/DRx/DW/ETF/warrant/suspended/illiquid rows.
- DR fair value, FX-adjusted tracking, local liquidity, bid/ask spread, and execution-quality research reports when local inputs exist.
- Yahoo-first dashboard source UX, config validation, local-reference Yahoo ticker selection, refresh/cache controls, stale/fallback warnings, and rerun-safe cache behavior.
- Opt-in backtest/risk throttle workflow using configured historical prices, including Yahoo-loaded history, with research-assumption labels and data coverage warnings.
- First-run Yahoo dependency diagnostics for missing `yfinance`.
- Explicit dashboard demo reference mode maps missing local reference paths to bundled fake/sample files at runtime only.
- Yahoo startup checklist reports active source, yfinance availability, configured tickers, cache status, reference coverage, demo mode state, manual fallback availability, and actionable blockers.
- Yahoo historical smoke test uses configured tickers and cache-first behavior and reports rows loaded, date range, cache status, warnings, and errors.
- Production reference readiness checks report missing files, required columns, fake/sample files, and local Yahoo ticker fields without inferring mappings or classifications.

## Current Constraints

- Do not invent market data, tickers, mappings, sectors, countries, liquidity, fair values, or security classifications.
- Do not add realtime feeds, scraping, API keys, broker integration, or live trading.
- Preserve CSV and manual upload fallback.
- Keep Yahoo historical/cache-based only.
- Keep local reference files as the source of truth for metadata, Thailand universe, DR/DRx mapping, security type, sector/country maps, and local DR quality data.
- Keep outputs labeled as research signals or research assumptions only.

## Recommended Next Work

### Phase 7F: Final Docs And Regression Tests

Goal: finalize first-run usability documentation and regression tests.

Expected scope:
- Update README, PROJECT_STATUS.md, RUN_STATE.md, PHASE_PLAN.md, and FIRST_RUN_USABILITY_PLAN.md.
- Document first-run install/run commands, demo vs production reference mode, Yahoo historical/cache limitations, manual upload fallback, and common first-run errors.
- Confirm all tests use mocks/fake data and never call external network services.
- Do not add new product features beyond docs/final regression tests.
- Keep tests network-free.

### Production-Data Readiness

Goal: prepare the existing research workflow for real local data without adding new live data capabilities.

Expected scope:
- Inventory fake/demo sample files and identify verified local replacements needed for research use.
- Validate real local Thailand universe, security type, liquidity, sector/industry, and DR/DRx mapping files.
- Validate local metadata and Yahoo ticker fields without inferring missing symbols.
- Confirm cache behavior and manual fallback instructions remain clear.
- Add tests only when validation behavior changes.

### Documentation Maintenance

Goal: keep project handoff files aligned with implemented behavior.

Expected scope:
- Update `README.md`, `PROJECT_STATUS.md`, `RUN_STATE.md`, and this plan after meaningful workflow changes.
- Keep test commands and known Windows pytest cache warning documented.
- Avoid claiming unsupported realtime, broker, scraping, API-key, or advice functionality.
