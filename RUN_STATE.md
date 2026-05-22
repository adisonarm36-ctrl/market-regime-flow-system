# Run State

## Last Completed Work

Phase 3B: Hybrid Yahoo + Local Reference Data Integration.

The project is currently safe to continue from the existing codebase. CSV remains supported, Yahoo historical price loading is optional, and local reference data is required for metadata-driven layers.

## Current Test Result

`63 passed`

## Next Phase

Phase 4: Thailand Universe and DR Reference Data

## Exact Next Prompt

```text
Read AGENTS.md first.

Implement Phase 4: Thailand Universe and DR Reference Data.

Goal:
Create verified local-reference workflows for Thailand market universes and DR/DRx mappings without live APIs.

Tasks:
- Add configurable Thailand universe files for SET50, SET100, SET ex-DR, and mai.
- Add schema validation for Thailand security types, suspended flags, and liquidity fields.
- Add DR/DRx reference schema with underlying ticker, market, currency, ratio, and optional fair value inputs.
- Ensure Thailand domestic breadth excludes DR, DRx, DW, ETF, warrants, suspended, and illiquid securities.
- Add tests using fake/demo Thailand reference data only.
- Update dashboard status tables and README.
Constraints:
- No invented real market data.
- No scraping.
- No API keys.
- No buy/sell recommendations.
- Keep outputs as research signals only.
```

## Handoff Notes

- Read `AGENTS.md` before continuing.
- Do not add live APIs in Phase 4.
- Do not present fake/demo data as real market data.
- Preserve CSV fallback.
- Preserve Yahoo as historical price-only source.
- Keep DR/DRx separate from Thailand domestic breadth.
