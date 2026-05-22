# Project Status

## Current Project Status

- **Phase 1 Completed**: Core data layer, validation, returns, and CSV-first loading.
- **Phase 2 Completed**: Data adapter preparation with CSV/manual upload adapters and provider interfaces.
- **Phase 3A Completed**: Yahoo historical OHLCV adapter through yfinance with cache-first mode.
- **Phase 3B Completed**: Hybrid Yahoo + local reference data integration.
- **Phase 4 Completed**: Thailand Universe and DR Reference Data (config, schemas, domestic exclusions).
- **Phase 5A Completed**: DR Fair Value, FX-Adjusted Tracking, and Local Liquidity Inputs.
- **Current Test Result**: **72 passed** out of 72.
- Yahoo historical adapter works with cache-first mode.
- Hybrid Yahoo + local reference data workflow works.
- Thailand ex-DR and other breadth layers strictly exclude non-domestic proxies.
- DR/DRx execution-ready and fair-value evaluation models fully operational using local offline references.

## Important Architecture Decisions

- Yahoo provides historical OHLCV prices only.
- Metadata, sector maps, country maps, asset maps, DR mappings, and DR execution quality inputs must come from local files.
- No realtime data.
- No scraping.
- No API keys.
- Outputs are research signals only, not buy/sell recommendations.
- DRs are not part of Thailand domestic market breadth.
- Missing optional data should be reported as warnings and skipped where possible.

## Key Files Changed So Far

- `config/data_sources.yaml`
- `src/dr_valuation.py`
- `src/dr_quality.py`
- `src/topdown_pipeline.py`
- `src/data_quality.py`
- `src/dashboard.py`
- `src/report_generator.py`
- `README.md`
- `tests/`

## Known Remaining Gaps

- Backtest and risk throttle (Phase 5B/6).
