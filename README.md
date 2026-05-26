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

Yahoo mode is the preferred dashboard path for historical OHLCV prices and uses `yfinance` through the configured `YahooDataAdapter`. It is not realtime and does not use API keys, streaming, broker connections, or WebSockets.

Manual CSV upload remains available in the dashboard as an Advanced/Fallback workflow for audited local files, demos, or cases where Yahoo coverage/cache is unavailable. To use Yahoo, edit `config/data_sources.yaml`:

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

Then run the dashboard. `Config source` is the default sidebar workflow and displays `active_source`, Yahoo historical/not-realtime status, cache path, cache availability, and cache last-updated timestamp when available.

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
- Thailand Reference Status
- Thailand Domestic Breadth Eligibility
- Thailand DR / DRx Reference
- Pipeline Layer Status
- reference warnings
- tickers missing metadata

## Thailand Reference Data Workflow

Phase 4 adds local-reference workflows for Thailand universes and DR/DRx mappings. No live APIs, scraping, API keys, or realtime inputs are used. Yahoo, when configured, remains historical price-only.

Thailand sample reference files live in `data/reference/thailand/` and are fake/demo data only:

- `thailand_universe_sample.csv`
- `thailand_sector_map_sample.csv`
- `thailand_security_types_sample.csv`
- `thailand_liquidity_sample.csv`
- `thailand_dr_mapping_sample.csv`

Required Thailand universe schema:

```csv
Ticker,Name,Country,Exchange,Universe,SecurityType,Sector,Industry,Currency,IsDR,IsDRx,IsETF,IsDW,IsWarrant,Suspended,IncludeInDomesticBreadth,Notes
```

Other Thailand reference schemas:

```csv
Ticker,Sector,Industry,Country,Exchange,Universe
Ticker,SecurityType,IsDomesticStock,IsDR,IsDRx,IsETF,IsDW,IsWarrant,Suspended,IncludeInDomesticBreadth,ExclusionReason
Ticker,average_traded_value_20d,average_volume_20d,trading_days_ratio_60d,liquidity_bucket,Notes
DR_Ticker,DR_Type,UnderlyingTicker,UnderlyingName,UnderlyingExchange,UnderlyingCountry,UnderlyingCurrency,DR_Currency,Ratio,IssuerCode,LocalExchange,IsActive,HasFairValueInput,FairValueSource,FXPair,Notes
```

Boolean-like fields accept `true/false`, `TRUE/FALSE`, `1/0`, `yes/no`, and `Y/N`. Missing required columns raise validation errors. Unknown `SecurityType` or `Universe` values are flagged as schema warnings, not silently accepted.

### Domestic Thailand Breadth Eligibility

Thailand domestic breadth uses local metadata only. A row is eligible only when it is a Thailand domestic common stock or equivalent, is not DR/DRx/ETF/DW/warrant, is not suspended, and has `IncludeInDomesticBreadth` set to true.

Optional local liquidity filters are configured in `config/thailand_universe.yaml`:

```yaml
liquidity_filter:
  min_avg_value_20d_thb: 5000000
  min_trading_days_ratio_60d: 0.85
```

DR/DRx are excluded because they are Thailand-listed proxy instruments for foreign underlyings. They must not be used to judge Thailand domestic market health. For DR/DRx, use the underlying instrument for signal and local DR data only for execution-quality research metrics.

### DR / DRx Mapping

Thailand DR/DRx mapping is loaded from local CSV reference data. The system groups DRs by underlying, identifies duplicate underlying groups, and ranks candidates from mapping-only or liquidity-supported inputs. Reference-only rankings are labeled with limited-confidence warnings and do not claim best tradable status without local liquidity, spread, tracking, or fair value data.

To add real Thailand data, replace the sample files with manually verified local files and update `config/data_sources.yaml` reference paths. Do not mix DR/DRx rows into the domestic universe. Do not add scraped data or live API credentials in these files.

## Phase 5A: DR Fair Value, FX-Adjusted Tracking, and Local Liquidity

Phase 5A enhances the research system with local market-data execution quality metrics, historical tracking, and quantitative mathematical valuation calculations for DR/DRx instruments.

### 1. Mathematical Valuation & Quality Formulas

* **DR Fair Value**: Calculated using the ratio convention of DR units per underlying unit:
  $$\text{fair\_value} = \left(\frac{\text{underlying\_price} \times \text{fx\_rate}}{\text{ratio}}\right) \times (1 - \text{fee\_adjustment\_pct})$$
  Only the `DR_per_Underlying` ratio convention is supported. If a different ratio convention is specified, the system flags a validation warning and skips calculation.
* **Premium / Discount**: Tells if a DR is trading above or below fair value:
  $$\text{premium\_discount\_pct} = \left(\frac{\text{dr\_price}}{\text{fair\_value}} - 1\right) \times 100$$
  * *Positive value*: DR trades at a premium (above fair value).
  * *Negative value*: DR trades at a discount (below fair value).
* **Bid-Ask Spread Percentage**:
  $$\text{bid\_ask\_spread\_pct} = \left(\frac{\text{ask} - \text{bid}}{\text{mid\_price}}\right) \times 100$$
* **FX-Adjusted Underlying Return**: Adjusts the underlying price for ratio and historical exchange rate:
  $$\text{fx\_adjusted\_price} = \frac{\text{underlying\_price} \times \text{fx\_rate}}{\text{ratio}}$$
  Returns are then calculated as daily percentage changes.
* **Tracking Correlation**: Rolling Pearson correlation between daily DR returns and daily FX-adjusted underlying returns.
* **Tracking Error**: Standard deviation of daily return differences between DR and FX-adjusted underlying:
  $$\text{tracking\_error} = \text{std}(\text{dr\_return} - \text{fx\_adjusted\_return}) \times 100$$

### 2. Capabilities Support Flags

The system dynamically determines and flags which data capabilities are active/supported for each instrument:
* `IsActive`: Loaded directly from mapping/reference data (never dynamically overwritten).
* `LiquiditySupported`: Requires `average_traded_value_20d >= 10,000` AND `trading_days_ratio_60d >= 0.1`.
* `SpreadSupported`: Bid/ask spread is available (i.e. `spread_pct` is not NaN).
* `FairValueSupported`: Fair value inputs, FX rate, and underlying prices are available (i.e. `premium_discount_pct` is not NaN).
* `TrackingSupported`: DR pricing and FX-adjusted underlying prices are available (i.e. `tracking_correlation` is not NaN).

### 3. Execution Ready & Confidence Levels

* **Execution Ready Label**: Strictly requires:
  * `IsActive == True`
  * `LiquiditySupported == True`
  * `SpreadSupported == True`
* **Confidence Level Buckets**:
  * **High**: All 4 capabilities are supported (`LiquiditySupported`, `SpreadSupported`, `FairValueSupported`, `TrackingSupported` are all True).
  * **Medium**: Liquidity and Spread are supported, but fair value or tracking data is missing.
  * **Low**: Otherwise (e.g. mapping-only DRs or insufficient data).

### 4. Data Quality & Coverage Summaries

To ensure robust data health reporting, Phase 5A introduces three specialized coverage checkers:
* `summarize_dr_execution_quality_data`: Reports counts of loaded DR market rows, spread rows, unique tickers, and average bid-ask spread.
* `summarize_dr_fair_value_coverage`: Identifies tickers in fair value inputs missing underlying price history or FX rate series, and calculates coverage percentages.
* `summarize_dr_tracking_coverage`: Measures date alignment and overlap counts between DR prices, underlying prices, and FX rates to assess tracking error calculation readiness.

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
- Thailand reference sample files are fake/demo data only.
- Real Thailand universes, sectors, security types, and DR mappings must be verified manually before research use.
- No official exchange calendars.
- Flow is a price-based proxy unless actual fund-flow data is supplied.
- DR fair value, FX-adjusted tracking, bid/ask spread, and tracking quality require local market data inputs.
- Dashboard expects CSV inputs and does not persist user settings.
- Sample data is fake/demo data only.

## Roadmap

Phase A: Data adapters and Yahoo historical adapter

Phase B: Real Thailand universe

Phase C: DR fair value/tracking

Phase D: Backtest/risk throttle

## Why Research Signals Only

Market data can be incomplete, delayed, adjusted, or structurally different across countries and instruments. The system therefore reports transparent metrics and classifications, not financial advice or guaranteed trading instructions.
