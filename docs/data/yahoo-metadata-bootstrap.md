# Yahoo Metadata Bootstrap

Phase 8A adds a local bootstrap workflow that asks Yahoo/yfinance for reference-data candidates for configured Yahoo tickers.

The output files are candidates only. They are marked `Source = Yahoo`, `VerificationStatus = NeedsReview`, and `IsYahooDerived = true`. Do not treat them as verified production reference files until a human reviews and manually promotes rows.

Rows that use conservative fallback values are also marked `IsFallbackDerived = true` and list the affected fields in `FallbackFields` or `MissingFields`/`Notes`. Fallback-derived values are review aids only, not verified production classifications.

## What Yahoo Can Fill

When available from yfinance, the bootstrap writes:

- `YahooTicker`
- `Ticker`
- `Name`
- `SecurityType` / Yahoo `quoteType`
- `Sector`
- `Industry`
- `Country`
- `Exchange`
- `Currency`
- `MarketCap`
- historical start/end coverage from Yahoo history
- recent 20-row average volume as a liquidity proxy

Yahoo coverage is incomplete and can vary by ticker, exchange, and instrument type.

## What Yahoo Cannot Fill Safely

Yahoo-derived metadata is not verified production reference data. It cannot safely replace:

- Thailand domestic universe membership
- Thailand security type eligibility
- DR/DRx mappings
- DR execution-quality files
- local liquidity, bid/ask, fair-value, FX, or underlying-price inputs
- manually verified sector, country, and asset classifications

The workflow does not write `data/reference/metadata.csv`, `data/reference/sector_map.csv`, `data/reference/country_map.csv`, or production asset-map files. It only writes generated candidate files.

## Commands

Use configured Yahoo tickers from `config/data_sources.yaml`:

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_yahoo_reference_data.py
```

Pass explicit tickers:

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_yahoo_reference_data.py --tickers SPY QQQ BTC-USD
```

Choose an output directory:

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_yahoo_reference_data.py --output-dir data/reference/generated
```

Review existing generated outputs without fetching:

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_yahoo_reference_data.py --validate-existing --output-dir data/reference/generated
```

## Generated Files

Generated CSV outputs are local artifacts under `data/reference/generated/` and are ignored by git:

- `yahoo_metadata_candidates.csv`
- `yahoo_sector_map_candidates.csv`
- `yahoo_country_map_candidates.csv`
- `yahoo_asset_map_candidates.csv`
- `yahoo_download_report.csv`
- `yahoo_promotion_review_report.csv`

Only `.gitkeep` is tracked so the directory exists.

The sector and country map candidate files include `YahooTicker`, provenance flags, missing-field notes, and `VerificationStatus = NeedsReview` so they can be reviewed before promotion. The download report includes map-generation status text for each ticker explaining whether a sector/country row came from Yahoo metadata, from a conservative fallback, or was not generated because no safe value existed.

## Conservative Fallbacks

The bootstrap uses conservative fallback labels only for obvious cases:

- tickers ending in `-USD` are candidate crypto rows with `Country = Global`, `Sector = Crypto`, and `AssetClass = Crypto`
- configured/sample asset-map hints may be copied into candidate asset-map rows for review
- configured/sample asset-map `asset_class` values may be used as review-only sector candidates when Yahoo sector is missing

Unknown tickers keep missing sector/country/asset fields blank. The script does not invent real classifications.

## Manual Promotion

To promote candidates manually:

1. Open the generated candidate CSVs.
2. Verify each ticker, name, type, sector, industry, country, exchange, currency, and asset class from trusted sources.
3. Remove or fill missing fields intentionally.
4. Copy reviewed rows into the production CSV/YAML files.
5. Keep or add notes that identify review date and source.

DR/DRx mappings and Thailand-specific DR quality files are intentionally left for a later user-provided data phase.
