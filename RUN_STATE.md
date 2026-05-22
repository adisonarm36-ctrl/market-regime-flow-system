# Run State

## Last Completed Work

Phase 4: Thailand Universe and DR Reference Data.

The project is currently safe to continue from the existing codebase. CSV remains supported, Yahoo historical price loading is optional, and Thailand metadata, universe membership, security type flags, liquidity references, and DR/DRx mappings are local-reference workflows.

## Current Test Result

`76 passed`

## Next Phase

Phase 5: DR Fair Value, FX-Adjusted Tracking, and Local Liquidity Inputs

Alternative: Phase 5: Backtest and Risk Throttle

## Exact Next Prompt

```text
Read AGENTS.md first.

Implement Phase 5: DR Fair Value, FX-Adjusted Tracking, and Local Liquidity Inputs.

Goal:
Add local-file support for DR fair value, FX-adjusted tracking, spreads, and execution-quality inputs without live APIs or scraping.

Tasks:
- Add local fair value and FX input schemas.
- Add local bid/ask spread input schemas.
- Calculate FX-adjusted DR tracking correlation when local inputs exist.
- Keep reference-only DR rankings clearly labeled as limited confidence when inputs are missing.
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
- Bundled Thailand reference files are fake/demo samples only.
