# Project Status

## Current Project Status

- Phase 1 completed: core data layer, validation, returns, and CSV-first loading.
- Phase 2 completed: data adapter preparation with CSV/manual upload adapters and provider interfaces.
- Phase 3A completed: Yahoo historical OHLCV adapter through yfinance with cache-first mode.
- Phase 3B completed: Hybrid Yahoo + local reference data integration.
- Current test result: 63 passed.
- CSV remains supported and is still the default fallback/source.
- Yahoo historical adapter works with cache-first mode.
- Hybrid Yahoo + local reference data workflow works.

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
- `src/topdown_pipeline.py`
- `src/dashboard.py`
- `README.md`
- `tests/`

## Known Remaining Gaps

- Real Thailand universe files are missing.
- DR/DRx mapping needs verified local reference data.
- DR fair value and FX-adjusted tracking are not implemented yet.
- Bid/ask spread needs local market data input.
- Backtest and risk throttle are not implemented yet.

## Next Phase

Phase 4: Thailand Universe and DR Reference Data
