# Phase Plan

Current implementation focus: Phase 5B backtesting workflow.

## Phase 5B-1: Backtest Core Engine and Risk Throttle

Goal: add a reusable backtest engine for research signals without producing financial advice.

Expected scope:
- Signal-to-position simulation using configured research signals.
- Portfolio and instrument return calculation from adjusted close where available.
- Risk throttle rules such as max exposure, volatility filter, drawdown guard, and cash allocation.
- Metrics including total return, volatility, max drawdown, hit rate, turnover, and exposure.
- Tests for return alignment, risk throttle behavior, missing data handling, and metrics.

## Phase 5B-2: Backtest Integration with Topdown Pipeline

Goal: connect backtest inputs and outputs to the existing top-down research pipeline.

Expected scope:
- Use existing country, sector, cluster, stock, DR, and redundancy outputs as signal inputs.
- Keep Thailand domestic breadth separate from DR/foreign proxy instruments.
- Treat DR signals as underlying-driven and execution quality as local DR-driven.
- Report missing data clearly and skip affected layers.
- Tests for pipeline integration, DR separation, and missing-data behavior.

## Phase 5B-3: Backtest Dashboard and Report Export

Goal: expose backtest results in Streamlit and daily exports.

Expected scope:
- Add dashboard views for backtest summary, risk throttle state, exposures, and performance metrics.
- Export CSV and HTML report sections.
- Label all outputs as research signals, not advice.
- Include the metrics behind every conclusion.
- Tests or smoke checks for export generation and dashboard data preparation.

## Constraints Across Phase 5B

- Do not invent market data.
- Do not hardcode fake financial data except in tests.
- Use config files for thresholds, universes, and mappings.
- Preserve CSV loading and configured adapter behavior.
- Do not mix DR/DRx into Thailand domestic breadth.
- Keep implementation modular and covered by focused pytest tests.
