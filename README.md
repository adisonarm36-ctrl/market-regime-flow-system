# market-regime-flow-system

Python + Streamlit research system for top-down global market analysis.

This project outputs research signals only. It does not provide financial advice, guaranteed buy/sell recommendations, or invented market data.

## Current Status

V1 stabilization is CSV-first and runnable with bundled fake/demo sample data. No live APIs are connected.

Implemented:

- OHLCV CSV loading and validation
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
- config and metadata validation helpers
- end-to-end sample data smoke test

## Install

```powershell
cd C:\Users\USER\Documents\AI\market-regime-flow-system
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Run Dashboard

From the project root:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Or:

```powershell
.\run_app.bat
```

Open:

```text
http://localhost:8501
```

In the sidebar, either upload CSV files or enable `Use bundled fake/demo sample data`.

## Sample Data

Sample files live in `data/sample/`.

They are fake/demo data for smoke testing only. They are not real tickers, prices, sectors, countries, DR mappings, or financial data.

Files:

- `prices_sample.csv`
- `metadata_sample.csv`
- `asset_map_sample.csv`
- `dr_mapping_sample.csv`
- `dr_mapping_sample.yaml`

The sample includes normal stocks, one DR, one ETF, and one DW-style excluded security. Thailand domestic breadth excludes the DR, ETF, and DW from domestic market health.

## Expected CSV Schemas

OHLCV:

```csv
Date,Ticker,Open,High,Low,Close,Volume,Adjusted Close
```

`Adjusted Close` is optional but preferred. If adjusted close is missing, `Close` is used.

Metadata:

```csv
Ticker,SecurityType,Country,Sector,Industry,Universe,Suspended,average_traded_value_20d
```

DR mapping CSV:

```csv
DR_Ticker,Underlying_Ticker,Description
```

Asset mapping CSV:

```csv
Ticker,asset_class,group,subgroup
```

Country map CSV, optional if metadata is supplied:

```csv
Ticker,Country
```

## Architecture

Top-down flow:

1. Global Money Flow
2. Country Market Breadth
3. Sector / Industry Breadth
4. Theme / Correlation Cluster
5. Stock / DR Selection
6. Execution Quality
7. Dashboard and Daily Report

Key modules:

- `src/data_loader.py`: CSV load and pivots
- `src/data_adapters/`: data source adapter interfaces and CSV/manual-upload adapters
- `src/data_validation.py`: OHLCV validation
- `src/global_flow.py`: price-based flow proxy
- `src/country_breadth.py`: country breadth metrics
- `src/thailand_breadth.py`: Thailand domestic breadth and exclusions
- `src/sector_breadth.py`: sector/industry aggregation
- `src/correlation.py` and `src/clustering.py`: correlation cluster analysis
- `src/momentum.py`: momentum metrics
- `src/redundancy.py`: redundancy detection
- `src/dr_mapping.py` and `src/dr_quality.py`: DR mapping and execution quality
- `src/stock_selection.py`: research candidate ranking
- `src/topdown_pipeline.py`: end-to-end pipeline
- `src/report_generator.py`: CSV/HTML report outputs
- `src/dashboard.py`: Streamlit UI
- `src/config_validation.py`: config and metadata validation helpers

## Config

Config files live in `config/`.

- `data_sources.yaml`: active data source and source-specific paths
- `global_flow.yaml`: asset-class buckets and optional benchmark ticker
- `country_universe.yaml`: country-to-ticker universe lists
- `thailand_universe.yaml`: Thailand universe lists and exclusion rules
- `sector_map.yaml`: sector and industry mappings
- `asset_map.yaml`: asset class, group, and subgroup mappings
- `dr_mapping.yaml`: DR-to-underlying mappings
- `regime_thresholds.yaml`: breadth regime thresholds
- `flow_thresholds.yaml`: flow proxy classification thresholds

No config file contains real tickers by default. Add verified tickers only from your own data source.

## Data Adapter Architecture

The adapter layer prepares the project for future real market data sources without hardcoding any provider.

Adapter interface:

- `load_prices()`
- `load_metadata()`
- `load_sector_map()`
- `load_dr_mapping()`
- `validate_schema()`

Current adapters:

- `CsvDataAdapter`: default source for configured local CSV files
- `ManualUploadAdapter`: wraps already-uploaded dashboard CSV dataframes
- `YahooDataAdapter`: optional yfinance historical data adapter with cache-first loading

Provider placeholders:

- `SettradeDataAdapter`
- `StooqDataAdapter`
- `InvestingDataAdapter`

The remaining placeholders intentionally raise `NotImplementedError`. They do not call APIs, scrape websites, or assume provider behavior.

## Using CSV Source

Default config:

```yaml
active_source: csv
source_settings:
  csv:
    price_path:
    metadata_path:
    sector_map_path:
    dr_mapping_path:
```

Example:

```yaml
active_source: csv
source_settings:
  csv:
    price_path: data/sample/prices_sample.csv
    metadata_path: data/sample/metadata_sample.csv
    sector_map_path: data/sample/asset_map_sample.csv
    dr_mapping_path: data/sample/dr_mapping_sample.csv
```

Programmatic usage:

```python
from src.config_loader import load_yaml
from src.data_adapters import get_data_adapter

config = load_yaml("config/data_sources.yaml")
adapter = get_data_adapter(config)
warnings = adapter.validate_schema()
prices = adapter.load_prices()
```

## Using Yahoo Historical Source

Yahoo mode is optional and uses `yfinance` for delayed historical data. It is not realtime and does not use API keys, streaming, or WebSockets.

CSV remains the default. To enable Yahoo, edit `config/data_sources.yaml`:

```yaml
active_source: yahoo
source_settings:
  yahoo:
    tickers:
      - SPY
      - QQQ
      - IWM
      - TLT
      - IEF
      - SHY
      - GLD
      - SLV
      - USO
      - UUP
      - BTC-USD
      - ETH-USD
    period: 2y
    interval: 1d
    auto_adjust: true
    cache_dir: data/cache/yahoo
    cache_format: parquet
    cache_ttl_hours: 8
    fallback_to_cache: true
    reference_data:
      metadata_path: data/reference/metadata.csv
      sector_map_path: data/reference/sector_map.csv
      country_map_path: data/reference/country_map.csv
      asset_map_path: config/asset_map.yaml
      dr_mapping_path: config/dr_mapping.yaml
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then run the dashboard and choose `Config source` in the sidebar:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

### Yahoo Cache Behavior

- If cache exists and is fresh, the adapter loads cache first.
- If cache is stale, the adapter fetches historical data from yfinance and updates cache.
- If fetch fails and `fallback_to_cache: true`, stale cache is used with a warning.
- If fetch fails and no cache exists, the adapter raises a clear error.
- Cache file names are deterministic from tickers, period/start/end, interval, and auto-adjust settings.

For daily research, `cache_ttl_hours: 8` is a reasonable twice-daily refresh setting. Increase it if you only refresh once per trading day.

### Yahoo Limitations

- Yahoo/yfinance mode is not realtime.
- `yfinance` is not affiliated with Yahoo.
- This adapter is intended for research and educational workflows.
- Yahoo ticker coverage may be incomplete.
- Thailand and DR tickers must be validated before use.
- Metadata, sector maps, and DR mappings still need local CSV/config files.
- No buy/sell recommendations are generated.

## Hybrid Yahoo + Local Reference Data

Yahoo/yfinance is used for historical OHLCV prices only. Metadata and mappings stay local because Yahoo metadata coverage can be incomplete and is not suitable for Thailand domestic breadth, DR mapping, or custom research universes.

Local reference data can provide:

- metadata
- sector map
- country map
- asset map
- DR mapping

Required metadata columns:

```csv
Ticker,SecurityType,Country,Sector,Industry,Universe,Suspended
```

Optional metadata columns:

```csv
Name,Currency,Exchange,IsDR,UnderlyingTicker,average_traded_value_20d,Notes
```

Reference sample files are in `data/reference/` and are fake/demo data only:

- `metadata_sample.csv`
- `sector_map_sample.csv`
- `country_map_sample.csv`

To add Thailand tickers, add verified tickers and metadata rows to your local reference CSV. Thailand domestic breadth excludes DR, DRx, DW, ETF, warrant, suspended, and illiquid securities based on local metadata.

To add DR mappings, add local rows with:

```csv
DR_Ticker,Underlying_Ticker
```

If the dashboard shows missing metadata warnings:

- confirm the Yahoo ticker exactly matches the local `Ticker` value
- confirm the metadata file path in `config/data_sources.yaml`
- check `reference_data_report` for tickers where `has_metadata` is false
- check `pipeline_layer_status` for skipped layers and reasons

In dashboard `Config source` mode, the app displays:

- Data Source Status
- Reference Data Status
- Pipeline Layer Status
- reference warnings
- tickers missing metadata

## Future Live Adapter Rules

Future live adapters should:

- implement `src.data_adapters.base.DataAdapter`
- require explicit config and tests before use
- never hardcode API keys
- never scrape websites unless a compliant, permissioned source is documented
- preserve CSV as the default fallback
- report missing data instead of inventing values

## Report Outputs

Reports include actual metric values and use research-signal wording. They must not be read as buy/sell recommendations.

Export helpers:

- `export_report_to_csv(outputs, output_dir)`
- `export_report_to_html(report_sections, path)`

## Current Limitations

- Yahoo/yfinance historical adapter is available, but no realtime or streaming adapters are implemented.
- No official exchange calendars.
- Flow is a price-based proxy unless actual fund-flow data is supplied.
- DR fair value, FX-adjusted tracking, and bid/ask spread are calculated only when matching data is supplied.
- Dashboard expects CSV inputs and does not persist user settings.
- Sample data is fake/demo data only.

## Roadmap

Phase A: Data adapters and Yahoo historical adapter

Phase B: Real Thailand universe

Phase C: DR fair value/tracking

Phase D: Backtest/risk throttle

## Why Research Signals Only

Market data can be incomplete, delayed, adjusted, or structurally different across countries and instruments. The system therefore reports transparent metrics and classifications, not financial advice or guaranteed trading instructions.
