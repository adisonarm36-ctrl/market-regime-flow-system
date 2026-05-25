# Run State

## Last Completed Work

Phase 5A: DR fair value and execution quality workflow has been merged into `main`.

The project is currently safe to continue from the existing codebase. CSV remains supported, Yahoo historical price loading is optional, and Thailand metadata, universe membership, security type flags, liquidity references, DR/DRx mappings, fair value inputs, FX-adjusted tracking, and execution-quality workflows are local-reference workflows.

## Current Test Result

`86 passed` on 2026-05-25 with Python 3.14.2.

## Next Phase

Phase 5B-1: Backtest Core Engine and Risk Throttle.

## Exact Next Prompt

```text
Read AGENTS.md, CODEX_WORKFLOW.md, RUN_STATE.md, PROJECT_STATUS.md, PHASE_PLAN.md, and TROUBLESHOOTING.md first.

Implement Phase 5B-1: Backtest Core Engine and Risk Throttle.

Goal:
Add a reusable backtest core engine and risk throttle for research signals only.

Tasks:
- Add signal-to-position simulation using configured research signals.
- Calculate backtest metrics from adjusted close when available.
- Add risk throttle rules such as max exposure, volatility filter, drawdown guard, and cash allocation.
- Handle missing data by reporting and skipping affected layers.
- Add focused pytest coverage using fake/demo data only.
Constraints:
- No invented real market data.
- No buy/sell recommendations.
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
