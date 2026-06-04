# Yahoo Candidate Review Worksheet

Generated Yahoo candidate CSVs in this directory are review inputs only. They are not verified production reference data. Do not change `VerificationStatus` from `NeedsReview`, promote rows, or copy values into production reference files until a human reviewer verifies each row against trusted sources.

## Candidate Files

| Candidate file | Rows | Needs review | Production target after human approval |
| --- | ---: | ---: | --- |
| `yahoo_metadata_candidates.csv` | 12 | 12 | `data/reference/metadata.csv` |
| `yahoo_sector_map_candidates.csv` | 12 | 12 | `data/reference/sector_map.csv` |
| `yahoo_country_map_candidates.csv` | 2 | 2 | `data/reference/country_map.csv` |
| `yahoo_asset_map_candidates.csv` | 12 | 12 | Production asset map configured by `config/data_sources.yaml` |

All candidate rows currently have `VerificationStatus=NeedsReview`.

## Metadata Candidates

Review source: `yahoo_metadata_candidates.csv`

Rows:

| Ticker | Yahoo ticker | Security type | Candidate sector | Candidate industry | Candidate country | Exchange | Currency | Human verification required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPY | SPY | ETF | Demo Equity | blank | blank | PCX | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| QQQ | QQQ | ETF | Demo Equity | blank | blank | NGM | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| IWM | IWM | ETF | Demo Equity | blank | blank | PCX | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| TLT | TLT | ETF | Demo Bonds | blank | blank | NGM | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| IEF | IEF | ETF | Demo Bonds | blank | blank | NGM | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| SHY | SHY | ETF | Demo Bonds | blank | blank | NGM | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| GLD | GLD | ETF | Demo Commodities | blank | blank | PCX | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| SLV | SLV | ETF | Demo Commodities | blank | blank | PCX | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| USO | USO | ETF | Demo Commodities | blank | blank | PCX | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| UUP | UUP | ETF | Demo Currency | blank | blank | PCX | USD | Verify ticker identity, name, security type, exchange, currency, sector, industry, and country. Replace demo sector if promoted. |
| BTC-USD | BTC-USD | CRYPTOCURRENCY | Crypto | Crypto | Global | CCC | USD | Verify ticker identity, crypto classification, sector, industry, country/global classification, exchange, and currency. |
| ETH-USD | ETH-USD | CRYPTOCURRENCY | Crypto | Crypto | Global | CCC | USD | Verify ticker identity, crypto classification, sector, industry, country/global classification, exchange, and currency. |

Fields requiring human verification:

- `Ticker`
- `YahooTicker`
- `Name`
- `SecurityType`
- `Sector`
- `Industry`
- `Country`
- `Exchange`
- `Currency`
- `MarketCap`, if used
- `RecentAverageVolume20D`, if used for production quality checks
- Any value marked fallback-derived or demo-derived

## Sector Map Candidates

Review source: `yahoo_sector_map_candidates.csv`

Rows:

| Ticker | Yahoo ticker | Candidate sector | Candidate industry | Human verification required |
| --- | --- | --- | --- | --- |
| SPY | SPY | Demo Equity | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| QQQ | QQQ | Demo Equity | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| IWM | IWM | Demo Equity | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| TLT | TLT | Demo Bonds | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| IEF | IEF | Demo Bonds | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| SHY | SHY | Demo Bonds | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| GLD | GLD | Demo Commodities | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| SLV | SLV | Demo Commodities | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| USO | USO | Demo Commodities | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| UUP | UUP | Demo Currency | blank | Verify production sector and industry. Candidate sector is fallback/demo-derived. |
| BTC-USD | BTC-USD | Crypto | Crypto | Verify production sector and industry. Candidate values are fallback-derived. |
| ETH-USD | ETH-USD | Crypto | Crypto | Verify production sector and industry. Candidate values are fallback-derived. |

Fields requiring human verification:

- `Ticker`
- `YahooTicker`
- `Sector`
- `Industry`
- Any blank `Industry` value
- Any fallback-derived sector or industry value

## Country Map Candidates

Review source: `yahoo_country_map_candidates.csv`

Rows:

| Ticker | Yahoo ticker | Candidate country | Human verification required |
| --- | --- | --- | --- |
| BTC-USD | BTC-USD | Global | Verify whether `Global` is the intended production country classification for this crypto instrument. |
| ETH-USD | ETH-USD | Global | Verify whether `Global` is the intended production country classification for this crypto instrument. |

Fields requiring human verification:

- `Ticker`
- `YahooTicker`
- `Country`
- Any fallback-derived country value

## Asset Map Candidates

Review source: `yahoo_asset_map_candidates.csv`

Rows:

| Ticker | Candidate asset class | Candidate group | Candidate subgroup | Human verification required |
| --- | --- | --- | --- | --- |
| SPY | Demo Equity | Demo Risk Assets | Demo Broad Market | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| QQQ | Demo Equity | Demo Risk Assets | Demo Growth Proxy | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| IWM | Demo Equity | Demo Risk Assets | Demo Small Cap Proxy | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| TLT | Demo Bonds | Demo Defensive Assets | Demo Long Treasury | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| IEF | Demo Bonds | Demo Defensive Assets | Demo Intermediate Treasury | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| SHY | Demo Bonds | Demo Defensive Assets | Demo Short Treasury | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| GLD | Demo Commodities | Demo Real Assets | Demo Gold Proxy | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| SLV | Demo Commodities | Demo Real Assets | Demo Silver Proxy | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| USO | Demo Commodities | Demo Real Assets | Demo Oil Proxy | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| UUP | Demo Currency | Demo Defensive Assets | Demo USD Proxy | Verify production asset class, group, and subgroup. Candidate values are copied from configured/sample mapping. |
| BTC-USD | Crypto | Alternative Assets | Crypto | Verify production asset class, group, and subgroup. |
| ETH-USD | Crypto | Alternative Assets | Crypto | Verify production asset class, group, and subgroup. |

Fields requiring human verification:

- `Ticker`
- `asset_class`
- `group`
- `subgroup`
- Any value copied from configured/sample mappings

## Exact Manual Review Steps

1. Open the candidate CSVs in `data/reference/generated/`.
2. For each row, verify ticker identity and classification against trusted reference sources.
3. Fill missing values only after verification. Do not infer missing values from price history alone.
4. Replace demo or fallback-derived values with production-ready values when trusted sources confirm them.
5. Keep rows as `NeedsReview` until a human reviewer explicitly approves the exact row.
6. After human verification, update candidate statuses to `Reviewed` or `Approved` only when explicitly authorized.
7. Run `scripts/promote_yahoo_candidates.py` without `--apply` to inspect the dry-run promotion report.
8. Review dry-run coverage gaps, skipped rows, and target-file changes.
9. Run `scripts/promote_yahoo_candidates.py --apply` only after explicit human approval.
10. Re-run production readiness checks and tests after any approved production reference changes.

## Prohibited During Review Support

- Do not mark generated candidate rows `Reviewed` or `Approved` without explicit human verification.
- Do not run `scripts/promote_yahoo_candidates.py --apply` without explicit human approval.
- Do not modify production reference CSVs as part of worksheet creation.
- Do not commit generated candidate CSVs.
- Do not invent ticker mappings, sector classifications, country mappings, security types, asset classes, liquidity values, fair values, FX values, or DR mappings.
