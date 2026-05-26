# Run State

## Last Completed Work

Phase 5A: DR fair value and execution quality workflow has been merged into `main`.

The project is currently safe to continue from the existing codebase. CSV remains supported, Yahoo historical price loading is optional, and Thailand metadata, universe membership, security type flags, liquidity references, DR/DRx mappings, fair value inputs, FX-adjusted tracking, and execution-quality workflows are local-reference workflows.

## Current Test Result

`86 passed` on 2026-05-25 with Python 3.14.2.

## Next Phase

Phase 6C: Universe/Ticker Management.

## Exact Next Prompt

```text
Read AGENTS.md, CODEX_WORKFLOW.md, RUN_STATE.md, PROJECT_STATUS.md, PHASE_PLAN.md, and TROUBLESHOOTING.md first.

Implement Phase 6C: Universe/Ticker Management.

Goal:
Add local reference-driven universe selection that can generate Yahoo ticker lists where local Yahoo ticker fields are configured.

Tasks:
- Add local reference-driven ticker universe selection.
- Allow selected universe to generate a Yahoo ticker list where possible.
- Warn when Yahoo ticker format is missing or not configured.
- Preserve Thailand domestic breadth exclusions.
- Add tests using mocks/fake data only.
Constraints:
- No invented real market data.
- No realtime, scraping, API keys, broker integration, or buy/sell recommendations.
- Keep outputs as research signals only.
```

## Handoff Notes

- Read `AGENTS.md` before continuing.
- Read `CODEX_WORKFLOW.md`, `PROJECT_STATUS.md`, `PHASE_PLAN.md`, and `TROUBLESHOOTING.md` before coding.
- Do not add live APIs unless a later phase explicitly requires and configures them.
- Do not present fake/demo data as real market data.
- Preserve CSV fallback.
- Preserve Yahoo as historical price-only source.
- Keep DR/DRx separate from Thailand domestic breadth.
- Bundled Thailand reference files are fake/demo samples only.
- Use feature branches for new implementation work.
- Yahoo historical data is price-only; local reference files remain required for metadata, Thailand universe, DR/DRx mapping, security type, sector/country maps, and local DR quality data.
- Do not invent Yahoo ticker mappings.
