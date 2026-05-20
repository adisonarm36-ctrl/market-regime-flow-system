# market-regime-flow-system

Python + Streamlit research system for top-down global market analysis.

This project outputs research signals only. It does not provide financial advice, guaranteed buy/sell recommendations, or invented market data.

## Architecture

Top-down flow:

1. Global Money Flow
2. Country Market Breadth
3. Sector / Industry Breadth
4. Theme / Correlation Cluster
5. Stock / DR Selection
6. Execution Quality
7. Dashboard and Daily Report

Current implementation covers Phase 1 to Phase 13:

- CSV OHLCV loading and validation
- adjusted close support when available
- price and volume pivots
- simple and log returns
- price-based global flow proxy scores
- country breadth and regime classification
- Thailand domestic breadth with DR/DRx/DW/ETF/warrant/suspended/illiquid exclusion
- sector and industry breadth
- correlation clustering and cluster ranking
- momentum and redundancy engines
- DR / DRx mapping and execution quality ranking
- stock research candidate ranking
- top-down pipeline outputs
- Streamlit dashboard
- CSV and HTML report generation

Outputs remain research signals only and should be read with the underlying metric columns.

## Data Format

CSV input must include:

```csv
Date,Ticker,Open,High,Low,Close,Volume
```

Optional adjusted close columns:

```csv
Adjusted Close
Adj Close
```

The loader uses adjusted close when available. If adjusted close is missing, `Close` is used and validation emits a warning.

## Config

Config files live in `config/`.

- `global_flow.yaml`: asset-class buckets and optional benchmark ticker
- `country_universe.yaml`: country-to-ticker universe lists
- `thailand_universe.yaml`: Thailand universe lists and exclusion rules
- `sector_map.yaml`: sector and industry mappings
- `asset_map.yaml`: asset class, group, and subgroup mappings
- `dr_mapping.yaml`: DR-to-underlying mappings
- `regime_thresholds.yaml`: breadth regime thresholds
- `flow_thresholds.yaml`: flow proxy classification thresholds

No config file contains invented tickers by default. Add real tickers only from your verified data source.

## Adding Countries

Add country universe members to `config/country_universe.yaml`, then provide matching OHLCV rows in CSV. If configured tickers are not present in the price data, the country layer reports missing data instead of guessing.

## Adding Thailand Universe

Add verified SET50, SET100, SET ex-DR, and mai members to `config/thailand_universe.yaml`. Thailand domestic breadth requires metadata with at least:

```csv
Ticker,SecurityType
```

Optional metadata columns:

```csv
Universe,Suspended,average_traded_value_20d,Sector
```

DR, DRx, DW, ETF, warrant, suspended, and illiquid securities are excluded from domestic Thailand breadth.

## Adding DR Mapping

Add mappings to `config/dr_mapping.yaml` in later Phase 9 work. DR signals must use the underlying instrument. DR price and liquidity data should only be used for execution quality.

## Run Tests

```powershell
pytest
```

## Run Dashboard

Run:

```powershell
.\.venv\Scripts\streamlit.exe run src/dashboard.py
```

Then upload CSV files from the sidebar. At minimum, upload OHLCV data with the required data format above.

## Limitations

- No live API adapters in the first version.
- Flow is a price-based proxy unless actual fund-flow data is supplied.
- Missing data is reported and skipped.
- Dashboard uses uploaded CSV data only. No live API adapters are enabled by default.

## Why Research Signals Only

Market data can be incomplete, delayed, adjusted, or structurally different across countries and instruments. The system therefore reports transparent metrics and classifications, not financial advice or guaranteed trading instructions.
