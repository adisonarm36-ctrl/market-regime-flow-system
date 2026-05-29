# Momentum Dashboard Phase Execution Runbook

## Purpose

This runbook is the reusable execution guide for the remaining Momentum Dashboard UX implementation phases. It converts the redesign plan into phase-sized work that can be run safely, reviewed independently, merged to `main`, and stopped before the next phase begins.

The dashboard must remain a research-signal dashboard. It must not provide financial advice, buy/sell recommendations, guaranteed outcomes, live trading, broker integration, scraping, API keys, realtime data, or invented market data.

## Global Execution Rules

- Run exactly one phase at a time.
- Start every phase from the latest `main`.
- Stop after the phase is merged to `main`, `main` is pushed, and final tests/checks are complete.
- Do not continue to the next phase automatically.
- Do not force push.
- Do not run `git reset --hard`.
- Do not commit `data/cache`.
- If untracked `data/cache` exists, inspect it first. Remove it only after confirming it is runtime Yahoo cache.
- If any other dirty files exist before phase work starts, stop and report them.
- Do not touch secrets, `.env`, tokens, credentials, cookies, private keys, or local auth files.
- Do not add live trading, broker integration, scraping, API keys, realtime feeds, or buy/sell recommendation language.
- Keep outputs labeled as research signals, research assumptions, flow signals, rotation signals, or relative strength signals.
- Do not change financial, signal, ranking, or backtest calculations unless the phase explicitly requires it and the user approves it.
- Preserve existing behavior unless the phase specifically changes presentation.
- Keep demo/sample data warnings and production-reference warnings visible.
- Keep Yahoo/yfinance historical and cache-based only.
- Keep manual upload fallback available.
- Keep DR/DRx separated from Thailand domestic market breadth.
- For DR/DRx, signal evidence must come from the underlying where existing logic does that; local DR data is for execution quality.

## Required Start Checklist For Every Phase

Run these before creating the phase branch:

```powershell
git checkout main
git pull origin main
git status --short
git branch --show-current
git log --oneline -5 --decorate
git remote -v
```

If `git status --short` shows only untracked `data/cache/`, inspect it:

```powershell
rg --files data\cache
```

If the files are runtime Yahoo cache, remove them:

```powershell
Remove-Item -Recurse -Force data\cache -ErrorAction SilentlyContinue
git status --short
```

Stop if any other dirty file remains.

Create the phase branch only after `main` is clean and current:

```powershell
git checkout -b <BRANCH_NAME>
```

## Required End Checklist For Every Phase

Before commit:

```powershell
git status --short
git diff --stat
git diff --name-status
```

Run the focused phase commands listed below, then the full command:

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
```

For documentation-only changes, tests are optional under `CODEX_WORKFLOW.md`, but implementation phases should run focused tests and full tests unless the user explicitly scopes the phase to docs only.

Commit and push:

```powershell
git add <changed-files>
git commit -m "<COMMIT_MESSAGE>"
git push -u origin <BRANCH_NAME>
```

Merge safely into `main` only after status is clean, changed files match the phase, and tests pass:

```powershell
git checkout main
git pull origin main
git merge --no-ff <BRANCH_NAME>
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git push origin main
```

Stop after `main` is pushed. Do not start the next phase in the same run unless the user explicitly asks after reviewing the completed phase.

## Phase 2: Today Decision Hub

### Goal

Add a first-screen decision overview that helps the user quickly review market regime, top research signals, data-quality alerts, strategy health, data freshness, and available actions from existing pipeline outputs.

### Scope

- Add a Today Decision Hub as the default or first review page.
- Include Market Regime, Top Signals, Risk Alerts, Strategy Health, Data Freshness, and Quick Actions sections.
- Use existing outputs only, including `global_flow_summary`, `country_breadth_summary`, `thailand_market_health`, `sector_breadth_summary`, `stock_ranking`, `momentum_summary`, `pipeline_layer_status` where available, warnings, and cache/source metadata.
- Add clear empty states for missing outputs.
- Keep raw supporting tables accessible but secondary.
- Keep no-advice and research-signal language visible.

### Out Of Scope

- New financial calculations.
- New ranking/scoring logic.
- Backtest calculation changes.
- Report/export implementation changes.
- Data adapter, cache, scraping, realtime, API-key, or broker changes.
- Root static prototype changes unless explicitly confirmed active.

### Branch Name

`phase2-momentum-today-decision-hub`

### Commit Message

`ui: add momentum today decision hub`

### Files Likely To Inspect/Change

- `src/dashboard.py`
- `tests/test_dashboard_yahoo_first.py`
- `tests/test_backtest_dashboard_report.py`
- `docs/design/momentum-dashboard-redesign.md`
- `docs/design/momentum-dashboard-baseline-inspection.md`

### Files Not To Touch

- `.env`
- secrets, tokens, credentials, cookies, private keys
- `data/cache/`
- `src/backtest.py`
- `src/momentum.py`
- `src/topdown_pipeline.py` unless strictly needed for presentation wiring and approved
- `src/data_adapters/`
- `config/data_sources.yaml` unless explicitly requested
- production or demo data files

### Safety Rules

- Do not claim actual money flow unless actual fund-flow data exists.
- Use "flow signal", "rotation signal", "relative strength signal", "research signal", and "review" language.
- Do not hide demo/sample data warnings.
- Do not hide stale cache or missing production-reference warnings.
- Do not trigger Yahoo downloads on rerun unless the user explicitly requests refresh through existing controls.
- Empty or missing outputs must render as unavailable, not fabricated.

### Focused Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_backtest_dashboard_report.py --basetemp=tmp_pytest
```

### Full Test Command

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Manual Dashboard Checklist

- Dashboard starts from Streamlit through `app.py`.
- Today Decision Hub appears as the first review surface.
- Config source mode still works.
- Manual upload remains reachable as Advanced/Fallback.
- Demo reference warnings remain visible.
- Yahoo historical/cache labels remain visible.
- Top Signals handles missing name, sector, industry, scores, or warnings without invented values.
- Risk Alerts shows warnings from data quality, cache, reference, DR quality, and backtest when available.
- Mobile/narrow viewport shows stacked sections without horizontal overflow.
- Raw tables remain available in collapsible or secondary sections.

### Merge-To-Main Steps

```powershell
git status --short
git diff --stat
git diff --name-status
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_backtest_dashboard_report.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git add src\dashboard.py tests\test_dashboard_yahoo_first.py tests\test_backtest_dashboard_report.py
git commit -m "ui: add momentum today decision hub"
git push -u origin phase2-momentum-today-decision-hub
git checkout main
git pull origin main
git merge --no-ff phase2-momentum-today-decision-hub
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git push origin main
```

### Stop Conditions

- Any dirty file other than confirmed runtime Yahoo cache exists before starting.
- The hub requires new financial calculations.
- The hub changes pipeline, ranking, signal, or backtest semantics.
- Tests fail and the failure is not understood.
- Dashboard startup fails.
- Any buy/sell recommendation language appears.

### Definition Of Done

- Today Decision Hub renders from existing outputs.
- Empty, warning, demo, stale cache, and missing-reference states are visible.
- Existing pages remain available.
- Focused and full tests pass.
- Branch is pushed, merged into `main`, `main` is pushed, and final `git status --short` is clean.

## Phase 3: Signal Cards And Filters

### Goal

Replace the primary stock-ranking review experience with scan-friendly research signal cards and filters while preserving access to the raw `stock_ranking` table.

### Scope

- Build a card view for `stock_ranking` and related available fields.
- Add filters for sector, country, confidence/data quality, signal type, badge, and failed-filter state where fields exist.
- Keep raw table access available.
- Show missing fields as "Not available" or "Needs data source".
- Ensure filtering does not mutate source data or change ranking calculations.

### Out Of Scope

- New momentum, trend, confidence, or risk calculations.
- Watchlist persistence unless separately approved.
- New data schema fields.
- Backtest changes.
- Report/export changes.
- Static root HTML/JS/CSS changes unless explicitly approved.

### Branch Name

`phase3-momentum-signal-cards-filters`

### Commit Message

`ui: add momentum signal cards and filters`

### Files Likely To Inspect/Change

- `src/dashboard.py`
- `tests/test_dashboard_yahoo_first.py`
- `tests/test_backtest_dashboard_report.py`
- `src/stock_selection.py` for output field names only
- `docs/design/momentum-dashboard-redesign.md`
- `docs/design/momentum-dashboard-baseline-inspection.md`

### Files Not To Touch

- `.env`
- secrets, tokens, credentials, cookies, private keys
- `data/cache/`
- `src/stock_selection.py` logic unless explicitly approved
- `src/momentum.py`
- `src/redundancy.py`
- `src/topdown_pipeline.py`
- `src/backtest.py`
- `src/backtest_integration.py`
- data/reference files
- config files unless explicitly requested

### Safety Rules

- Derive card fields only from existing columns.
- Do not invent trend, confidence, risk, or badge values.
- If a badge needs a threshold and no threshold exists, label it unavailable or omit it.
- Failed-filter signals must remain clear and must not be silently promoted.
- DR/DRx cards must not imply they belong to Thailand domestic breadth.
- Raw source table must remain inspectable.

### Focused Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_sample_pipeline_smoke.py --basetemp=tmp_pytest
```

### Full Test Command

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Manual Dashboard Checklist

- Stock Ranking or Signal Explorer page shows stacked signal cards.
- Filters work independently and together.
- Clearing filters restores the original candidate list.
- Raw `stock_ranking` table remains available.
- Missing metadata renders as unavailable.
- Failed filters and data-quality warnings are visible.
- Mobile/narrow viewport does not require horizontal scrolling for primary card review.
- No new recommendation language appears.

### Merge-To-Main Steps

```powershell
git status --short
git diff --stat
git diff --name-status
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_sample_pipeline_smoke.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git add src\dashboard.py tests\test_dashboard_yahoo_first.py tests\test_backtest_dashboard_report.py
git commit -m "ui: add momentum signal cards and filters"
git push -u origin phase3-momentum-signal-cards-filters
git checkout main
git pull origin main
git merge --no-ff phase3-momentum-signal-cards-filters
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git push origin main
```

### Stop Conditions

- Card labels require invented metrics.
- Filtering changes source DataFrame contents or ranking semantics.
- Raw ranking table is removed.
- DR/DRx or Thailand domestic breadth boundaries become unclear.
- Tests fail or dashboard cannot start.

### Definition Of Done

- Signal cards render from existing `stock_ranking` fields.
- Filters preserve source data and ranking semantics.
- Raw table remains available.
- Focused and full tests pass.
- Branch is pushed, merged into `main`, `main` is pushed, and final status is clean.

## Phase 4: Signal Detail View

### Goal

Add a single-signal explanation view that shows why a signal exists, which metrics support it, what data is missing, and what warnings apply.

### Scope

- Add detail page, drawer, or selected-signal state in the active Streamlit dashboard.
- Show decision summary, signal breakdown, data quality, warning status, and supporting raw rows.
- Use existing price or indicator data only if already available in dashboard outputs.
- Show unavailable sections explicitly.
- Handle ordinary stocks, DR/DRx signals, and missing metadata.

### Out Of Scope

- New indicators.
- New charts that require new calculations.
- Persistent watchlists.
- Changes to DR mapping logic.
- Changes to Thailand domestic breadth logic.
- Backtest calculation changes.
- Export behavior changes.

### Branch Name

`phase4-momentum-signal-detail-view`

### Commit Message

`ui: add momentum signal detail view`

### Files Likely To Inspect/Change

- `src/dashboard.py`
- `tests/test_dashboard_yahoo_first.py`
- `tests/test_backtest_dashboard_report.py`
- `src/topdown_pipeline.py` for output keys only
- `src/dr_mapping.py` for existing DR field semantics only
- `docs/design/momentum-dashboard-redesign.md`
- `docs/design/momentum-dashboard-baseline-inspection.md`

### Files Not To Touch

- `.env`
- secrets, tokens, credentials, cookies, private keys
- `data/cache/`
- `src/dr_mapping.py` logic unless explicitly approved
- `src/thailand_breadth.py`
- `src/momentum.py`
- `src/backtest.py`
- `src/backtest_integration.py`
- reference data and config files

### Safety Rules

- Do not calculate new signal evidence in the UI.
- Do not mix DR/DRx into Thailand domestic market breadth.
- Do not imply missing price history exists.
- Do not infer missing mappings, sectors, countries, or classifications.
- Keep ticker-level warnings visible.
- Detail language must explain evidence and limits, not recommend trades.

### Focused Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_thailand_breadth_eligibility.py tests\test_dr_execution_quality.py --basetemp=tmp_pytest
```

### Full Test Command

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Manual Dashboard Checklist

- User can open a detail view from a signal card or ranking row.
- Detail view shows symbol, metadata, signal score fields, warnings, and source rows.
- Missing metadata shows unavailable labels.
- DR/DRx detail keeps underlying signal evidence and DR execution-quality data conceptually separate where present.
- Detail view does not invent benchmark, volume, chart, or risk values.
- User can return to the signal list without losing dashboard stability.
- Mobile/narrow viewport renders without overflow.

### Merge-To-Main Steps

```powershell
git status --short
git diff --stat
git diff --name-status
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_thailand_breadth_eligibility.py tests\test_dr_execution_quality.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git add src\dashboard.py tests\test_dashboard_yahoo_first.py tests\test_backtest_dashboard_report.py
git commit -m "ui: add momentum signal detail view"
git push -u origin phase4-momentum-signal-detail-view
git checkout main
git pull origin main
git merge --no-ff phase4-momentum-signal-detail-view
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git push origin main
```

### Stop Conditions

- Detail sections require unapproved new calculations.
- DR/DRx handling becomes ambiguous.
- Missing metadata is inferred instead of reported.
- Dashboard state becomes unstable.
- Tests fail or dashboard cannot start.

### Definition Of Done

- Detail view explains one signal using existing data.
- Missing data and warning states are visible.
- DR/DRx and Thailand domestic breadth separation is preserved.
- Focused and full tests pass.
- Branch is pushed, merged into `main`, `main` is pushed, and final status is clean.

## Phase 5: Backtest Evidence UX

### Goal

Make opt-in backtest outputs easier to interpret without changing backtest calculations or implying future performance.

### Scope

- Improve dashboard presentation of existing `backtest_summary`, `backtest_portfolio`, `backtest_positions`, `backtest_instrument_metrics`, and `backtest_warnings`.
- Explain existing fields such as `hit_rate`, `max_drawdown`, `observations`, `turnover`, and `average_gross_exposure`.
- Add sample-size and coverage warnings using existing warning outputs.
- Keep research-assumption and no-advice labels prominent.
- Preserve empty state when backtest is disabled or unavailable.

### Out Of Scope

- New backtest metrics.
- Changes to signal generation.
- Changes to portfolio construction, throttles, exposure rules, or DR backtest mapping.
- New export formats.
- Live or realtime performance tracking.

### Branch Name

`phase5-momentum-backtest-evidence-ux`

### Commit Message

`ui: improve momentum backtest evidence view`

### Files Likely To Inspect/Change

- `src/dashboard.py`
- `src/report_generator.py` only if display helper text is reused without changing export behavior
- `tests/test_backtest.py`
- `tests/test_backtest_integration.py`
- `tests/test_backtest_dashboard_report.py`
- `tests/test_report_generator.py`
- `docs/design/momentum-dashboard-redesign.md`
- `docs/design/momentum-dashboard-baseline-inspection.md`

### Files Not To Touch

- `.env`
- secrets, tokens, credentials, cookies, private keys
- `data/cache/`
- `src/backtest.py` calculation logic
- `src/backtest_integration.py` signal and alignment logic
- `src/stock_selection.py`
- `src/momentum.py`
- data/reference files
- config files unless explicitly approved

### Safety Rules

- Label all backtest results as historical research assumptions only.
- Do not imply predictive accuracy or future performance.
- Do not rename `hit_rate` into "win probability"; use historical hit rate.
- Do not show average return or setup count unless those outputs already exist.
- Coverage warnings must remain visible.
- Failed-filter and missing-underlying behavior must remain unchanged.

### Focused Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_backtest.py tests\test_backtest_integration.py tests\test_backtest_dashboard_report.py tests\test_report_generator.py --basetemp=tmp_pytest
```

### Full Test Command

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Manual Dashboard Checklist

- Backtest page shows clear disabled/empty state when backtest is not enabled.
- Existing summary metrics render with plain-language explanations.
- Warnings show missing common dates, missing common tickers, missing prices, missing signals, limited observations, stale Yahoo/cache, and demo/sample limitations when present.
- Portfolio, positions, and instrument metrics remain inspectable.
- No future-performance or buy/sell language appears.
- Existing report/export behavior still works.

### Merge-To-Main Steps

```powershell
git status --short
git diff --stat
git diff --name-status
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_backtest.py tests\test_backtest_integration.py tests\test_backtest_dashboard_report.py tests\test_report_generator.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git add src\dashboard.py src\report_generator.py tests\test_backtest_dashboard_report.py tests\test_report_generator.py
git commit -m "ui: improve momentum backtest evidence view"
git push -u origin phase5-momentum-backtest-evidence-ux
git checkout main
git pull origin main
git merge --no-ff phase5-momentum-backtest-evidence-ux
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git push origin main
```

### Stop Conditions

- UX requires changing backtest calculations.
- Existing warnings become less visible.
- Backtest labels imply future results.
- Tests fail or backtest fixtures need invented data beyond tests.
- Export behavior changes unintentionally.

### Definition Of Done

- Backtest evidence view explains existing outputs clearly.
- Research-assumption and no-advice language is visible.
- Backtest calculations and semantics are unchanged.
- Focused and full tests pass.
- Branch is pushed, merged into `main`, `main` is pushed, and final status is clean.

## Phase 6: Narrative Report Export UX

### Goal

Improve the report review and export experience around existing CSV and HTML export behavior.

### Scope

- Show report sections before export.
- Keep supported export formats grounded in implementation: CSV and HTML.
- Improve narrative review layout for market summary, top signals, key risks, backtest evidence, data-quality notes, and appendix/raw data where existing outputs support them.
- Preserve existing `build_daily_report`, CSV export, and HTML export behavior unless explicitly approved.
- Keep Markdown and PDF as future enhancements unless separately implemented and approved.

### Out Of Scope

- New export formats.
- PDF generation.
- Markdown export unless separately approved.
- Changes to report calculation inputs.
- Changes to backtest calculations.
- New data sources or live/realtime export workflows.

### Branch Name

`phase6-momentum-report-export-ux`

### Commit Message

`export: improve momentum report review ux`

### Files Likely To Inspect/Change

- `src/dashboard.py`
- `src/report_generator.py`
- `tests/test_report_generator.py`
- `tests/test_backtest_dashboard_report.py`
- `tests/test_sample_pipeline_smoke.py`
- `docs/design/momentum-dashboard-redesign.md`
- `docs/design/momentum-dashboard-baseline-inspection.md`

### Files Not To Touch

- `.env`
- secrets, tokens, credentials, cookies, private keys
- `data/cache/`
- `src/backtest.py`
- `src/backtest_integration.py`
- `src/topdown_pipeline.py` unless only reading output keys
- data/reference files
- config files
- dependency files unless explicitly approved

### Safety Rules

- Do not remove CSV or HTML export.
- Do not advertise Markdown or PDF as supported unless implemented and tested in an approved phase.
- Do not include buy/sell recommendation language in report sections.
- Keep fake/demo and missing production-reference warnings visible.
- Do not fabricate report sections from unavailable outputs.
- Do not change export file contents unexpectedly unless tests and scope explicitly cover that change.

### Focused Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_report_generator.py tests\test_backtest_dashboard_report.py tests\test_sample_pipeline_smoke.py --basetemp=tmp_pytest
```

### Full Test Command

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Manual Dashboard Checklist

- Daily Report or Report Export page previews report sections before export.
- CSV export still works.
- HTML export still works.
- Unsupported formats are not shown as available.
- Backtest evidence is labeled as research assumptions only.
- Data-quality and demo/sample notes are included or clearly linked.
- Raw output tables remain available where existing UI exposes them.

### Merge-To-Main Steps

```powershell
git status --short
git diff --stat
git diff --name-status
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_report_generator.py tests\test_backtest_dashboard_report.py tests\test_sample_pipeline_smoke.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git add src\dashboard.py src\report_generator.py tests\test_report_generator.py tests\test_backtest_dashboard_report.py
git commit -m "export: improve momentum report review ux"
git push -u origin phase6-momentum-report-export-ux
git checkout main
git pull origin main
git merge --no-ff phase6-momentum-report-export-ux
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git push origin main
```

### Stop Conditions

- Requested UX requires unsupported export formats.
- Report output would require invented metrics.
- Existing CSV/HTML behavior changes unexpectedly.
- Tests fail or export files cannot be generated.
- Any recommendation language appears.

### Definition Of Done

- Report preview UX reflects existing sections and outputs.
- CSV and HTML export remain supported and tested.
- Unsupported formats are clearly not presented as available.
- Focused and full tests pass.
- Branch is pushed, merged into `main`, `main` is pushed, and final status is clean.

## Phase 7: Polish, Accessibility, And Performance

### Goal

Refine readability, mobile responsiveness, accessibility, and rendering efficiency after the main UX phases are merged.

### Scope

- Verify mobile/narrow layout across dashboard pages.
- Reduce unnecessary raw table exposure by moving raw data behind secondary controls where appropriate.
- Add accessible labels and non-color-only status indicators.
- Improve empty, loading, and error states.
- Check heavy chart/table rendering behavior and avoid unnecessary rendering.
- Keep existing calculations and behavior stable.

### Out Of Scope

- New feature surfaces.
- New calculations.
- New dependencies unless explicitly approved.
- Architecture rewrites.
- Data adapter or cache behavior changes.
- Export format changes.
- Realtime, scraping, broker, API-key, or live trading work.

### Branch Name

`phase7-momentum-polish-accessibility-performance`

### Commit Message

`ui: polish momentum dashboard accessibility and performance`

### Files Likely To Inspect/Change

- `src/dashboard.py`
- `tests/test_dashboard_yahoo_first.py`
- `tests/test_backtest_dashboard_report.py`
- `tests/test_report_generator.py`
- `README.md` only if user-facing run instructions or accessibility notes materially change
- `docs/design/momentum-dashboard-redesign.md`
- `docs/design/momentum-dashboard-baseline-inspection.md`

### Files Not To Touch

- `.env`
- secrets, tokens, credentials, cookies, private keys
- `data/cache/`
- `src/backtest.py`
- `src/backtest_integration.py`
- `src/momentum.py`
- `src/topdown_pipeline.py`
- `src/data_adapters/`
- data/reference files
- config files unless explicitly requested

### Safety Rules

- Polish must not change research outputs.
- Accessibility work must not hide warnings or raw evidence.
- Performance work must not change calculation semantics or cache refresh semantics.
- Do not add dependencies without approval.
- Do not remove existing pages.
- Do not hide no-advice, demo, cache, or production-readiness labels.

### Focused Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_backtest_dashboard_report.py tests\test_report_generator.py --basetemp=tmp_pytest
```

### Full Test Command

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Manual Dashboard Checklist

- Desktop layout is readable.
- Mobile/narrow layout does not overflow.
- Buttons and controls have clear text labels.
- Status indicators do not rely on color alone.
- Empty states are direct and actionable.
- Error states do not expose raw tracebacks for expected optional-data issues.
- Large raw tables are secondary where possible.
- Dashboard reruns do not trigger Yahoo downloads unless existing explicit refresh controls are used.
- All major pages still load.
- No new dependency is required.

### Merge-To-Main Steps

```powershell
git status --short
git diff --stat
git diff --name-status
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_backtest_dashboard_report.py tests\test_report_generator.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git add src\dashboard.py tests\test_dashboard_yahoo_first.py tests\test_backtest_dashboard_report.py tests\test_report_generator.py README.md
git commit -m "ui: polish momentum dashboard accessibility and performance"
git push -u origin phase7-momentum-polish-accessibility-performance
git checkout main
git pull origin main
git merge --no-ff phase7-momentum-polish-accessibility-performance
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
git push origin main
```

### Stop Conditions

- Polish requires calculation, data, or architecture changes.
- Accessibility updates reduce warning visibility.
- Performance changes alter refresh/cache semantics.
- Tests fail or dashboard pages regress.
- New dependency becomes necessary without approval.

### Definition Of Done

- Dashboard is more readable and responsive.
- Accessibility labels and non-color-only status cues are improved.
- Existing behavior and calculations are unchanged.
- Focused and full tests pass.
- Branch is pushed, merged into `main`, `main` is pushed, and final status is clean.

## Phase Executor Prompt Template

Use this template to run one phase at a time.

```text
Read AGENTS.md, CODEX_WORKFLOW.md, TROUBLESHOOTING.md, RUN_STATE.md, PROJECT_STATUS.md, PHASE_PLAN.md, docs/design/momentum-dashboard-redesign.md, docs/design/momentum-dashboard-baseline-inspection.md, and docs/design/momentum-dashboard-phase-runbook.md first.

PHASE_TO_RUN:
<PHASE_TO_RUN>

BRANCH_NAME:
<BRANCH_NAME>

COMMIT_MESSAGE:
<COMMIT_MESSAGE>

Goal:
Execute only the named Momentum Dashboard UX phase from docs/design/momentum-dashboard-phase-runbook.md.

Rules:
- Start from latest main.
- Run only this phase.
- Do not continue to the next phase.
- Stop after merge to main, push main, and final tests/checks.
- Do not force push.
- Do not run git reset --hard.
- Do not commit data/cache.
- If untracked data/cache exists, inspect it and remove it only after confirming it is runtime Yahoo cache.
- If any other dirty files exist before work starts, stop and report.
- Do not touch secrets, .env, tokens, credentials, cookies, or private keys.
- No live trading, broker integration, scraping, API keys, realtime, or buy/sell recommendations.
- Keep outputs as research signals only.
- Do not change financial/backtest calculations unless explicitly required and approved.
- Preserve existing behavior unless the phase specifically changes presentation.

Required final response:
- phase run
- branch used
- commit hash
- merge commit hash
- files changed
- focused tests run
- full test result
- final git status
- recommended next phase
```

