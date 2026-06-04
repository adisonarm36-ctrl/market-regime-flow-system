# Yahoo Candidate Human Review Worksheet

This worksheet is for production data readiness review only. Do not treat any generated row as verified production data until a human has checked it against trusted sources.

Do not run promotion with `--apply` until manually reviewed rows are intentional and the dry-run output is acceptable.

## Candidate Files

- `yahoo_metadata_candidates.csv`
- `yahoo_sector_map_candidates.csv`
- `yahoo_country_map_candidates.csv`
- `yahoo_asset_map_candidates.csv`
- `yahoo_download_report.csv`
- `yahoo_promotion_review_report.csv`

## Tickers Included

- `SPY`
- `QQQ`
- `IWM`
- `TLT`
- `IEF`
- `SHY`
- `GLD`
- `SLV`
- `USO`
- `UUP`
- `BTC-USD`
- `ETH-USD`

## Trusted Source Types

Use source types that are appropriate for the field being verified:

- Ticker identity, name, exchange, currency: issuer website, exchange listing page, official fund page, regulated filing, or trusted market-data vendor.
- Security type: issuer website, exchange/security master, official fund page, or regulated filing.
- ETF sector, industry, and asset classification: issuer fund page, fund prospectus, index provider methodology, or internal approved taxonomy.
- Country classification: issuer domicile, primary listing country, underlying exposure methodology, or internal approved taxonomy.
- Crypto classification: internal approved taxonomy, exchange/security master, or formal project/asset documentation where appropriate.
- Historical start/end and volume fields: approved historical price source or existing configured data provider output.
- Market cap: approved market-data vendor or official provider. Leave blank if unavailable or not relevant for the instrument type.

Do not invent classifications. If a trusted source does not support a field, leave the row as `NeedsReview`.

## Review Checklist

- [ ] Confirm each ticker is intended for the production research universe.
- [ ] Confirm `Ticker` and `YahooTicker` mapping.
- [ ] Confirm `Name`.
- [ ] Confirm `SecurityType`.
- [ ] Confirm `Exchange`.
- [ ] Confirm `Currency`.
- [ ] Confirm `Sector`.
- [ ] Confirm `Industry`.
- [ ] Confirm `Country`.
- [ ] Confirm `asset_class`.
- [ ] Confirm `group`.
- [ ] Confirm `subgroup`.
- [ ] Confirm `MarketCap` only if relevant and supported by a trusted source.
- [ ] Confirm historical coverage fields if they will be relied on operationally.
- [ ] Confirm recent volume field if it will be used for liquidity or readiness review.
- [ ] Replace demo/fallback values only when a trusted source supports the replacement.
- [ ] Leave uncertain or unsupported fields blank or keep the row as `NeedsReview`.
- [ ] Run promotion dry-run before any apply step.
- [ ] Only human-reviewed rows should be changed from `NeedsReview` to `Reviewed` or `Approved`.

## Summary Of Gaps

### Metadata Gaps

- `SPY`, `QQQ`, `IWM`, `TLT`, `IEF`, `SHY`, `GLD`, `SLV`, `USO`, and `UUP` are missing `Industry` and `Country`.
- `SPY`, `QQQ`, `IWM`, `TLT`, `IEF`, `SHY`, `GLD`, `SLV`, `USO`, and `UUP` have blank `MarketCap`.
- `BTC-USD` and `ETH-USD` have populated crypto fallback values but still require human verification.

### Sector/Industry Gaps

- `SPY`, `QQQ`, and `IWM` use fallback sector `Demo Equity` and have blank `Industry`.
- `TLT`, `IEF`, and `SHY` use fallback sector `Demo Bonds` and have blank `Industry`.
- `GLD`, `SLV`, and `USO` use fallback sector `Demo Commodities` and have blank `Industry`.
- `UUP` uses fallback sector `Demo Currency` and has blank `Industry`.
- `BTC-USD` and `ETH-USD` use fallback `Sector=Crypto` and `Industry=Crypto`.

### Country Gaps

- No country-map candidate row exists for `SPY`, `QQQ`, `IWM`, `TLT`, `IEF`, `SHY`, `GLD`, `SLV`, `USO`, or `UUP`.
- `BTC-USD` and `ETH-USD` have fallback `Country=Global`.

### Asset Map Gaps

- `SPY`, `QQQ`, `IWM`, `TLT`, `IEF`, `SHY`, `GLD`, `SLV`, `USO`, and `UUP` use demo asset map labels copied from configured/sample mapping.
- `BTC-USD` and `ETH-USD` use crypto fallback asset map labels.
- All asset map rows remain `NeedsReview`.

### Rows That Should Stay NeedsReview

Rows should stay `NeedsReview` when:

- Any field is still based on a demo value.
- Any field is still based on a fallback value that has not been checked.
- `Industry`, `Country`, or any other required production field is blank and not explicitly accepted by the reviewer.
- The ticker is not intended for the production research universe.
- The reviewer cannot cite an appropriate trusted source type.

At the current inspection point, every generated candidate row should remain `NeedsReview` until a human reviewer verifies it.

## Row-Level Review Notes

| Ticker | Files | Missing fields | Current fallback/demo fields | Fields requiring human verification |
|---|---|---|---|---|
| `SPY` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Equity`; `asset_class=Demo Equity`; `group=Demo Risk Assets`; `subgroup=Demo Broad Market` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `QQQ` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Equity`; `asset_class=Demo Equity`; `group=Demo Risk Assets`; `subgroup=Demo Growth Proxy` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `IWM` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Equity`; `asset_class=Demo Equity`; `group=Demo Risk Assets`; `subgroup=Demo Small Cap Proxy` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `TLT` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Bonds`; `asset_class=Demo Bonds`; `group=Demo Defensive Assets`; `subgroup=Demo Long Treasury` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `IEF` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Bonds`; `asset_class=Demo Bonds`; `group=Demo Defensive Assets`; `subgroup=Demo Intermediate Treasury` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `SHY` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Bonds`; `asset_class=Demo Bonds`; `group=Demo Defensive Assets`; `subgroup=Demo Short Treasury` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `GLD` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Commodities`; `asset_class=Demo Commodities`; `group=Demo Real Assets`; `subgroup=Demo Gold Proxy` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `SLV` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Commodities`; `asset_class=Demo Commodities`; `group=Demo Real Assets`; `subgroup=Demo Silver Proxy` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `USO` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Commodities`; `asset_class=Demo Commodities`; `group=Demo Real Assets`; `subgroup=Demo Oil Proxy` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `UUP` | metadata, sector map, asset map | `Industry`, `Country`, `MarketCap`; no country-map row | `Sector=Demo Currency`; `asset_class=Demo Currency`; `group=Demo Defensive Assets`; `subgroup=Demo USD Proxy` | ticker mapping, name, security type, exchange, currency, sector, industry, country, asset class, group, subgroup, historical coverage, recent volume |
| `BTC-USD` | metadata, sector map, country map, asset map | none listed, but all crypto classifications are fallback-derived | `Sector=Crypto`; `Industry=Crypto`; `Country=Global`; `asset_class=Crypto`; `group=Alternative Assets`; `subgroup=Crypto` | ticker mapping, name, security type, exchange, currency, sector, industry, country/taxonomy, asset class, group, subgroup, market cap, historical coverage, recent volume |
| `ETH-USD` | metadata, sector map, country map, asset map | none listed, but all crypto classifications are fallback-derived | `Sector=Crypto`; `Industry=Crypto`; `Country=Global`; `asset_class=Crypto`; `group=Alternative Assets`; `subgroup=Crypto` | ticker mapping, name, security type, exchange, currency, sector, industry, country/taxonomy, asset class, group, subgroup, market cap, historical coverage, recent volume |

## Final Instruction

Only rows that have been checked by a human reviewer against trusted sources should be changed from `NeedsReview` to `Reviewed` or `Approved`. All other rows should remain `NeedsReview`.
