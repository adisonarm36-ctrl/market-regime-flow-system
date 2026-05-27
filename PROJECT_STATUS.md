# Project Status

## Current Project Status

- Phase 1 completed: core data layer, validation, returns, and CSV-first loading.
- Phase 2 completed: data adapter preparation with CSV/manual upload adapters and provider interfaces.
- Phase 3A completed: Yahoo historical OHLCV adapter through yfinance with cache-first mode.
- Phase 3B completed: Hybrid Yahoo + local reference data integration.
- Phase 4 completed: Thailand universe and DR/DRx local reference data workflows.
- Phase 5A completed: DR fair value, FX-adjusted tracking, and execution-quality workflow.
- Phase 6A-6F completed: Yahoo-first dashboard workflow, config validation, local ticker universe selection, refresh/cache controls, Yahoo-fed opt-in backtest, and documentation/test finalization.
- Current test result: 119 passed, 1 pytest cache warning on 2026-05-27 with Python 3.14.2.
- CSV remains supported and is still the default fallback/source.
- Yahoo historical adapter works with cache-first mode and explicit user-controlled refresh.
- Hybrid Yahoo + local reference data workflow works.
- Dashboard source UX now defaults to the configured source path, with manual upload kept as an Advanced/Fallback workflow.
- Yahoo-first config workflow now has clearer config defaults, validation helpers, partial-data warnings, dashboard cache fallback controls, stale-cache warnings, and fallback-to-cache warnings.
- Local reference-driven Yahoo ticker universe selection is available where verified Yahoo ticker fields exist.
- Opt-in research backtests can use Yahoo-loaded historical prices through the configured pipeline and include coverage warnings.
- Thailand reference schemas, domestic breadth eligibility, and DR/DRx mapping reports work with local files.
- DR fair value and execution-quality workflow is merged into `main`.

## Important Architecture Decisions

- Yahoo provides historical OHLCV prices only.
- Metadata, sector maps, country maps, asset maps, and DR mappings must come from local CSV/YAML files.
- No realtime data.
- No scraping.
- No API keys.
- Outputs are research signals only, not buy/sell recommendations.
- DR is not part of Thailand domestic market breadth.
- DR signal should come from the underlying instrument; local DR data is for execution quality.
- Missing optional data should be reported as warnings and skipped where possible.

## Key Files Changed So Far

- `config/data_sources.yaml`
- `src/data_adapters/`
- `src/reference_data.py`
- `src/data_quality.py`
- `src/thailand_reference.py`
- `src/thailand_breadth.py`
- `src/dr_mapping.py`
- `src/dr_quality.py`
- `src/dr_valuation.py`
- `src/dr_execution_quality.py`
- `src/topdown_pipeline.py`
- `src/dashboard.py`
- `data/reference/thailand/`
- `config/thailand_universe.yaml`
- `README.md`
- `tests/`

## Known Remaining Gaps

- Bundled Thailand reference files are fake/demo samples only.
- Real Thailand universe files must be manually verified before research use.
- DR/DRx mapping needs verified local reference data for production research.
- Backtest/risk throttle is implemented as research assumptions, but it still depends on configured historical data coverage and explicit user opt-in.
- Dashboard and report export for backtest results are available for existing backtest outputs, but real production use requires verified source data and review of assumptions.
- Yahoo-first workflow is complete through documentation/tests, but Yahoo coverage can still be partial or unavailable.

## Next Phase

No new feature phase is active. Recommended next work is production-data readiness: verify real local reference files, replace fake/demo samples where needed, and expand documentation/tests only when behavior changes.
