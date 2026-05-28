# Momentum Dashboard Baseline Inspection

## Scope

Phase 0 baseline inspection for the Momentum Dashboard Redesign Plan.

This is documentation/inspection only. No app code, dashboard UI, report/export behavior, backend logic, strategy logic, backtest logic, pipeline behavior, or financial calculations were changed.

## Branch and Baseline

- Current branch inspected: `phase0-momentum-dashboard-baseline-inspection`
- Baseline commit before this document: `10b6d77` (`Merge momentum dashboard redesign plan`)
- Active workspace path: `C:\Users\USER\Documents\AI\market-regime-flow-system`
- Workflow path substitution: `CODEX_WORKFLOW.md` references an Administrator path, but this session used the active project workspace path above.

## Files Inspected

- `AGENTS.md`
- `CODEX_WORKFLOW.md`
- `TROUBLESHOOTING.md`
- `RUN_STATE.md`
- `PROJECT_STATUS.md`
- `PHASE_PLAN.md`
- `YAHOO_FIRST_WORKFLOW_PLAN.md`
- `FIRST_RUN_USABILITY_PLAN.md`
- `docs/design/momentum-dashboard-redesign.md`
- `README.md`
- `app.py`
- `src/dashboard.py`
- `src/report_generator.py`
- `src/backtest.py`
- `src/backtest_integration.py`
- `src/topdown_pipeline.py`
- `requirements.txt`
- `index.html`
- `app.js`
- `styles.css`
- `sample-data.js`
- `tests/test_dashboard_yahoo_first.py`
- `tests/test_report_generator.py`
- `tests/test_backtest.py`
- `tests/test_backtest_integration.py`
- `tests/test_backtest_dashboard_report.py`
- Test suite file list under `tests/`

## Active Dashboard Entrypoint

- Active Python entrypoint: `app.py`
- `app.py` imports `main` from `src.dashboard` and runs it when invoked directly.
- README dashboard command points to Streamlit:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

## Active Streamlit Dashboard File

- Active Streamlit dashboard file: `src/dashboard.py`
- The dashboard calls `st.set_page_config`, uses Streamlit sidebar controls, and renders pages through `st.sidebar.radio`.
- Confirmed dashboard modes:
  - `Config source`
  - `Advanced / fallback manual upload`
- Confirmed dashboard pages in current code:
  - Global Flow Map
  - Country Market Health
  - Thailand Market Health
  - Thailand Reference Status
  - Sector Breadth
  - Theme / Correlation Cluster
  - Stock Ranking
  - DR Global Proxy
  - Redundancy Report
  - Backtest
  - Daily Report

## Root Static Files Status

Root static files are present:

- `index.html`
- `app.js`
- `styles.css`
- `sample-data.js`

Observed:

- `index.html` references `styles.css` and `app.js`.
- `app.js` reads `window.SAMPLE_SECURITIES`, which is defined in `sample-data.js`.
- `rg` found references to these files from `index.html` and documentation only.
- No Python/Streamlit runtime reference to these files was found during inspection.

Assessment:

- Active production dashboard appears to be Streamlit through `app.py` and `src/dashboard.py`.
- Root static HTML/JS/CSS appears to be a standalone static prototype or legacy dashboard shell.
- Unknown / needs inspection: whether the static root files are used by any external deployment path outside the Python/Streamlit workflow.

## Active Report and Export Files

- Active report/export implementation: `src/report_generator.py`
- Confirmed narrative report builder:
  - `build_daily_report(outputs)`
- Confirmed CSV export:
  - `export_report_to_csv(outputs, output_dir)`
- Confirmed HTML export:
  - `export_report_to_html(report_sections, path)`
- Confirmed backtest report table helper:
  - `build_backtest_report_tables(outputs)`
- Confirmed tests:
  - `tests/test_report_generator.py`
  - `tests/test_backtest_dashboard_report.py`
  - `tests/test_sample_pipeline_smoke.py`

Confirmed export formats:

- CSV
- HTML

Not confirmed:

- Markdown export
- PDF export

## Active Backtest Files

- Core backtest implementation: `src/backtest.py`
- Pipeline integration: `src/backtest_integration.py`
- Dashboard display helper: `build_backtest_dashboard_tables` in `src/dashboard.py`
- Report helper: `build_backtest_report_tables` in `src/report_generator.py`

Confirmed backtest outputs:

- `backtest_summary`
- `backtest_portfolio`
- `backtest_positions`
- `backtest_instrument_metrics`
- `backtest_warnings`

Confirmed backtest summary columns from sample inspection:

- `total_return`
- `annualized_volatility`
- `max_drawdown`
- `hit_rate`
- `turnover`
- `average_gross_exposure`
- `observations`
- `signal_type`

Confirmed safety language:

- Backtest output uses `research signal only`.
- Backtest warning text says historical research assumptions only and not financial advice.

## Active Pipeline Files

- Main orchestration: `src/topdown_pipeline.py`
- Relevant calculation modules used by the pipeline include:
  - `src/global_flow.py`
  - `src/country_breadth.py`
  - `src/thailand_breadth.py`
  - `src/sector_breadth.py`
  - `src/correlation.py`
  - `src/clustering.py`
  - `src/momentum.py`
  - `src/redundancy.py`
  - `src/stock_selection.py`
  - `src/dr_mapping.py`
  - `src/dr_quality.py`
  - `src/dr_valuation.py`
  - `src/data_quality.py`

Confirmed sample pipeline output keys:

- `global_flow_summary`
- `asset_class_flow_summary`
- `country_breadth_summary`
- `thailand_market_health`
- `breadth_timeseries`
- `included_securities`
- `excluded_securities`
- `excluded_summary`
- `thailand_eligibility_report`
- `thailand_excluded_securities`
- `sector_breadth_summary`
- `correlation_matrix`
- `cluster_membership`
- `cluster_summary`
- `momentum_summary`
- `redundancy_report`
- `dr_execution_quality_report`
- `dr_fair_value_report`
- `dr_tracking_report`
- `dr_liquidity_report`
- `dr_quality_warnings`
- `dr_quality_ranking`
- `stock_ranking`
- `backtest_summary`
- `backtest_portfolio`
- `backtest_positions`
- `backtest_instrument_metrics`
- `backtest_warnings`

Confirmed `momentum_summary` columns from sample inspection:

- `Ticker`
- `momentum_1m`
- `momentum_3m`
- `momentum_6m`
- `momentum_12m`
- `volatility_adjusted_momentum`
- `distance_from_52week_high`
- `above_50ma`
- `above_200ma`
- `trend_quality`
- `momentum_score`

Confirmed `stock_ranking` columns from sample inspection:

- `Ticker`
- `SecurityType`
- `Country`
- `Sector`
- `Industry`
- `Universe`
- `Suspended`
- `average_traded_value_20d`
- `momentum_1m`
- `momentum_3m`
- `momentum_6m`
- `momentum_12m`
- `volatility_adjusted_momentum`
- `distance_from_52week_high`
- `above_50ma`
- `above_200ma`
- `trend_quality`
- `momentum_score`
- `country_breadth_score`
- `country_regime`
- `sector_breadth_score`
- `cluster`
- `cluster_score`
- `dr_quality_score`
- `dr_data_quality_warning`
- `failed_filters`
- `data_quality_warning`
- `research_score`
- `reason`
- `signal_type`

## Test Command Found

README lists:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

`CODEX_WORKFLOW.md` uses the safer temp-dir form:

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

This inspection used the workflow command with `--basetemp=tmp_pytest`.

## Build/Lint Command Found

Build/compile command found in `CODEX_WORKFLOW.md`:

```powershell
.\.venv\Scripts\python.exe -m compileall src
```

Lint command:

- Not found.
- No lint tool is listed in `requirements.txt`.
- No separate lint command was identified during inspection.

## Current Verification Result

Pre-edit verification commands run:

```powershell
git status --short
git branch --show-current
git log --oneline -5 --decorate
git remote -v
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

Results:

- Branch confirmed: `phase0-momentum-dashboard-baseline-inspection`
- Initial git status: clean
- Python version: `Python 3.14.2`
- Compile result: passed
- Test result: `135 passed, 1 warning`

## Current Known Warnings

### Pytest cache warning

Observed warning:

```text
PytestCacheWarning: could not create cache path ... .pytest_cache\v\cache\nodeids: [WinError 183] Cannot create a file when that file already exists
```

This is already documented in `TROUBLESHOOTING.md` as a known Windows pytest cache warning. It did not affect pass/fail status.

### Streamlit `use_container_width` deprecation

`src/dashboard.py` still contains `st.dataframe(..., use_container_width=True)` usages.

Observed locations from `rg`:

- `src/dashboard.py`

Current status:

- Warning presence at runtime was not manually verified in this Phase 0 inspection.
- The code still contains deprecated-style usage that may trigger Streamlit deprecation warnings depending on installed Streamlit version.
- No code change was made in this docs-only phase.

## Current Dashboard Behavior Summary

Observed from `src/dashboard.py` and tests:

- Streamlit app title: `Market Regime Flow System`
- Dashboard starts with research-signal/no-advice language.
- Sidebar default data workflow is `Config source`.
- Manual upload remains available as `Advanced / fallback manual upload`.
- Config/Yahoo mode includes:
  - demo reference mode toggle
  - config validation warnings
  - Yahoo/yfinance dependency status
  - local Thailand Yahoo ticker universe option
  - cache fallback checkbox
  - refresh Yahoo historical data button
  - Yahoo cache metadata display
  - Yahoo startup checklist
  - Yahoo historical smoke test control
  - production reference readiness table
- Main pages currently lean heavily on raw `st.dataframe` tables.
- Daily Report page renders narrative sections from `build_daily_report`.
- Backtest page renders non-empty backtest output tables if opt-in backtest is enabled.
- DR Global Proxy page uses tabs for execution ranking, fair value, tracking, liquidity, and quality warnings.

Manual browser/dashboard run:

- Not run in this Phase 0 inspection because the task requested documentation/inspection only and safe verification commands were sufficient.

## Current Export Behavior Summary

Confirmed from `src/report_generator.py` and tests:

- `build_daily_report` returns narrative text sections:
  - `global_flow`
  - `country_regime`
  - `thailand_market`
  - `sector`
  - `cluster`
  - `stock_selection`
  - `dr_quality`
  - `backtest`
- `export_report_to_csv` exports non-empty DataFrame outputs to CSV files.
- `export_report_to_html` writes a simple HTML file containing report sections.
- Backtest report tables can be filtered to non-empty backtest output tables before CSV export.
- CSV and HTML are confirmed supported.
- Markdown/PDF export are not confirmed.

## Current Backtest Behavior Summary

Confirmed from `src/backtest.py`, `src/backtest_integration.py`, and tests:

- Backtests are opt-in research assumptions.
- Signals are converted to lagged positions.
- Exposure and position limits are enforced by `BacktestConfig`.
- Optional volatility/drawdown throttles exist.
- Backtest aligns prices and signals and reports missing common dates/tickers.
- Pipeline-generated signals use `stock_ranking.research_score`.
- DR signals map to underlying tickers when DR mapping and underlying price data exist.
- DR backtest signal is skipped when underlying price data is missing.
- Failed-filter signals are skipped.
- Backtest output includes portfolio path, positions, metrics, instrument metrics, and warnings.
- Backtest report language includes no-advice/research-assumption disclaimers.

## Unknowns and Assumptions

- Unknown / needs inspection: whether root static files are used in any deployment path outside the Streamlit workflow.
- Unknown / needs inspection: whether a watchlist feature exists. No active watchlist module or test was identified.
- Unknown / needs inspection: whether a production deployment expects root `index.html` instead of Streamlit.
- Unknown / needs inspection: exact behavior of Streamlit deprecation warnings in the installed Streamlit version.
- Unknown / needs inspection: whether manual browser/mobile visual checks should use Streamlit, the root static prototype, or both.
- Assumption: Phase 1 should target the Streamlit dashboard path first because README and `app.py` identify it as the active dashboard.
- Assumption: Root static files should not be changed in Phase 1 unless the user explicitly confirms they are active.
- Assumption: Phase 1 must not change pipeline/backtest/report calculations.

## Recommended Phase 1 Starting Scope

Phase 1 should be limited to a UI-only design system foundation for the active Streamlit dashboard:

- Add or identify pure UI presentation helpers for:
  - status badges
  - metric rows
  - empty states
  - warning blocks
  - compact cards
- Keep current dashboard pages and pipeline calls intact.
- Add tests only for pure helper behavior if helpers are introduced.
- Do not change:
  - `src/topdown_pipeline.py`
  - `src/backtest.py`
  - `src/backtest_integration.py`
  - `src/report_generator.py` export behavior
  - data schemas
  - strategy or financial calculations
- Treat root static files as out of scope until their active/legacy status is confirmed.

## Phase 0 Verification Checklist

- What changed?
  - Added this baseline inspection document only.
- Which files changed?
  - `docs/design/momentum-dashboard-baseline-inspection.md`
- Did we preserve existing behavior?
  - Yes. No source, config, test, pipeline, dashboard, backtest, or export code was changed.
- Did tests pass?
  - Yes. Pre-edit full suite: `135 passed, 1 warning`.
- Did build/compile pass?
  - Yes. `.\.venv\Scripts\python.exe -m compileall src` passed.
- Did manual dashboard check pass?
  - Not run; not required for this documentation-only inspection.
- Did mobile check pass?
  - Not run; Phase 0 did not launch the dashboard or browser.
- Any data-quality warnings?
  - Runtime data-quality warnings were not evaluated manually. Existing docs note fake/demo sample data and missing production references must remain visible.
- Any known risks?
  - Root static files may be legacy or may have an external deployment path not visible from code inspection.
  - Streamlit `use_container_width=True` deprecation may still appear at runtime.
- Is git status clean after commit?
  - To be checked after commit.

