# Phase Plan

Current implementation focus: Phase 8A.1 Yahoo candidate map generation fix.

The Yahoo-first transition is complete through Phase 6F. Phase 7A through 7F first-run usability work is complete. Phase 8A adds a Yahoo metadata bootstrap that writes generated NeedsReview candidate files without replacing production references. Phase 8A.1 improves generated sector/country map candidates so Yahoo metadata and conservative fallback values produce reviewable rows with provenance notes. Phase 8B adds a dry-run-first promotion workflow for manually Reviewed/Approved Yahoo candidate rows with backups before production CSV overwrite. The system supports configured CSV/manual data, optional Yahoo historical OHLCV loading, local reference-driven metadata/universe/mapping workflows, explicit Yahoo cache controls, opt-in research backtests from configured historical prices, missing-yfinance diagnostics, explicit runtime demo reference bootstrap mode, a Yahoo startup checklist before configured loading, an explicit Yahoo historical smoke test, production reference readiness checks, and finalized first-run documentation.

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
- First-run docs cover install/run commands, demo vs production reference mode, Yahoo historical/cache limitations, manual upload fallback, common first-run errors, and regression test expectations.
- Yahoo metadata bootstrap writes candidate metadata, sector, country, asset-map, download-report, and promotion-review CSVs under `data/reference/generated/`; generated CSVs are local ignored artifacts and all rows require manual review.
- Yahoo sector/country map candidates include `YahooTicker`, `IsFallbackDerived`, missing-field notes, and map-generation report status; fallback values remain review-only.
- Reviewed Yahoo candidate promotion is available as a user-run script; it blocks NeedsReview rows, reports coverage gaps, and backs up existing production CSVs before overwrite.

## Current Constraints

- Do not invent market data, tickers, mappings, sectors, countries, liquidity, fair values, or security classifications.
- Do not add realtime feeds, scraping, API keys, broker integration, or live trading.
- Preserve CSV and manual upload fallback.
- Keep Yahoo historical/cache-based only.
- Keep local reference files as the source of truth for metadata, Thailand universe, DR/DRx mapping, security type, sector/country maps, and local DR quality data.
- Keep Yahoo-derived metadata bootstrap outputs as generated candidates only; do not silently promote them into production CSV/YAML files.
- Promote Yahoo-derived candidates only through the explicit dry-run/apply workflow after manual review.
- Keep outputs labeled as research signals or research assumptions only.

## Recommended Next Work

### Production-Data Readiness

Goal: prepare the existing research workflow for real local data without adding new live data capabilities.

Expected scope:
- Inventory fake/demo sample files and identify verified local replacements needed for research use.
- Review Yahoo metadata candidates generated under `data/reference/generated/` and manually promote only verified rows.
- Use `scripts/promote_yahoo_candidates.py` dry-run before any `--apply` promotion.
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
