# Project Status

## Current Project Status

- Phase 1 completed: core data layer, validation, returns, and CSV-first loading.
- Phase 2 completed: data adapter preparation with CSV/manual upload adapters and provider interfaces.
- Phase 3A completed: Yahoo historical OHLCV adapter through yfinance with cache-first mode.
- Phase 3B completed: Hybrid Yahoo + local reference data integration.
- Phase 4 completed: Thailand universe and DR/DRx local reference data workflows.
- Current test result: 76 passed.
- CSV remains supported and is still the default fallback/source.
- Yahoo historical adapter works with cache-first mode.
- Hybrid Yahoo + local reference data workflow works.
- Thailand reference schemas, domestic breadth eligibility, and DR/DRx mapping reports work with local files.

## Important Architecture Decisions

- Yahoo provides historical OHLCV prices only.
- Metadata, sector maps, country maps, asset maps, and DR mappings must come from local CSV/YAML files.
- No realtime data.
- No scraping.
- No API keys.
- Outputs are research signals only, not buy/sell recommendations.
- DR is not part of Thailand domestic market breadth.
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
- DR fair value and FX-adjusted tracking are not implemented yet.
- Bid/ask spread needs local market data input.
- Backtest and risk throttle are not implemented yet.

## Next Phase

Phase 5: DR Fair Value, FX-Adjusted Tracking, and Local Liquidity Inputs

Alternative Phase 5: Backtest and Risk Throttle
