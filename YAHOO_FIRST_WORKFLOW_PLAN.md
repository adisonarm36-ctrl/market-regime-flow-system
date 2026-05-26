# Yahoo-First Workflow Plan

## Objective

Make the dashboard default to the configured Yahoo historical data workflow while keeping manual CSV upload as an optional fallback. Yahoo/yfinance is for historical OHLCV prices only. It is not realtime, not a source of reference truth, and must not be used for scraping, broker integration, API keys, or trading advice.

All outputs remain research signals only. Do not describe any output as financial advice, a buy/sell recommendation, or a future-return guarantee.

## Required Reading

Before implementing any phase, read:

1. `AGENTS.md`
2. `CODEX_WORKFLOW.md`
3. `TROUBLESHOOTING.md`
4. `RUN_STATE.md`
5. `PROJECT_STATUS.md`
6. `PHASE_PLAN.md`
7. `YAHOO_FIRST_WORKFLOW_PLAN.md`

## What Yahoo Can And Cannot Provide

Yahoo can provide:
- Historical OHLCV price data through the existing `YahooDataAdapter` / yfinance workflow.
- Adjusted close when available from the downloaded historical data.
- Historical volume where available.
- Cacheable historical price snapshots for repeatable local research runs.

Yahoo cannot provide authoritative project reference data:
- Thailand security classification.
- Thailand domestic universe membership.
- DR/DRx mapping.
- DR underlying mapping.
- Sector, industry, country, or asset-class maps.
- Suspended-security flags.
- Domestic liquidity eligibility.
- Local DR bid/ask spreads.
- Local DR fair-value inputs.
- Broker execution data.
- Realtime market data.

Local reference files remain required for metadata, Thailand universe, DR/DRx mapping, security type, sector/country maps, and local DR quality data.

## Why Manual Upload Still Exists

Manual upload remains as an Advanced/Fallback path because:
- Yahoo coverage can be partial or unavailable.
- Some tickers require local exchange-specific formatting.
- Users may need audited or vendor-provided historical files.
- Tests and demos should avoid network calls.
- Local CSV keeps research reproducible when cache or network access is unavailable.

Manual upload should not be removed. It should be visually secondary to Config/Yahoo mode.

## Exact Pre-Flight Commands

Use the active workspace path if the Administrator path is unavailable in the Codex sandbox, and report the substitution.

```powershell
cd C:\Users\Administrator\Documents\AI\market-regime-flow-system

git status --short
git branch --show-current
git log --oneline -5 --decorate
git remote -v

.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest

Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git status --short
```

## Exact Post-Work Commands

```powershell
git status --short
git diff --stat
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
Remove-Item -Recurse -Force tmp_pytest -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
git diff --stat
git diff --name-status
```

## Branch Workflow

Create one feature branch per phase from the latest reviewed base branch. Do not merge into `main` from Codex unless explicitly requested.

```powershell
git status --short
git branch --show-current
git checkout -b phase6a-yahoo-dashboard-source-ux
```

For later phases, use similarly scoped branch names:
- `phase6b-yahoo-config-workflow`
- `phase6c-universe-ticker-management`
- `phase6d-yahoo-refresh-cache-controls`
- `phase6e-backtest-yahoo-history`
- `phase6f-yahoo-docs-tests`

Commit and push:

```powershell
git add <relevant-files-only>
git commit -m "<clear commit message>"
git push -u origin HEAD
```

## Global Safety Rules

- Do not invent tickers, mappings, prices, sectors, countries, liquidity, fair value, or security classifications.
- Do not use scraping, API keys, broker integration, realtime feeds, or live trading features.
- Do not change tests to weaken safety expectations.
- Do not delete manual upload.
- Do not make Yahoo the source of truth for metadata or local reference data.
- Use mocks/fake data in tests; do not call external network in tests.
- Keep DR/DRx out of Thailand domestic breadth.
- Label dashboard and report outputs as research signals or research assumptions only.
- Report missing optional data clearly and skip affected layers.

## Phase 6A: Dashboard Source UX Cleanup

### Goal

Make Config/Yahoo source mode the default dashboard path and move manual upload into an Advanced/Fallback section without removing it.

### Files Likely To Change

- `src/dashboard.py`
- `tests/test_dashboard_yahoo_first.py` or equivalent dashboard-helper test file
- `README.md` only if this phase includes user-facing behavior notes

### Files Not To Touch

- `src/data_adapters/yahoo_adapter.py`
- `src/topdown_pipeline.py`
- `src/backtest.py`
- `src/backtest_integration.py`
- Secrets, `.env`, credentials, cookies, private keys

### Implementation Tasks

- Change dashboard source selection default from manual upload/sample to Config source.
- Rename or restructure manual upload as Advanced/Fallback UI.
- Show `active_source` from `config/data_sources.yaml` prominently.
- Show a clear notice that Yahoo mode is historical and not realtime.
- Show cache path, cache availability, and last updated timestamp when cache exists.
- Keep bundled fake/demo sample data available only as a demo/fallback.
- Avoid repeated source loads on Streamlit reruns by preserving existing cached loader patterns.

### Safety Rules

- Do not remove manual upload.
- Do not add network calls outside the existing adapter path.
- Do not claim Yahoo data is complete or authoritative.
- Do not add broker or execution wording.

### Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

All existing tests pass, plus focused dashboard helper tests pass without network access.

### Rollback Notes

Revert only dashboard UX/helper changes. Manual upload should still work if rollback is needed.

### Definition Of Done

- Config source is the default visible dashboard path.
- Manual upload is still available as fallback.
- Dashboard shows active source, Yahoo historical notice, cache path, and cache timestamp.
- No source-code constants require editing to switch normal cache behavior.

### Recommended Commit Message

`Make dashboard Yahoo config source the default`

## Phase 6B: Yahoo-First Config Workflow

### Goal

Make `config/data_sources.yaml` clear and self-validating for Yahoo-first historical data usage.

### Files Likely To Change

- `config/data_sources.yaml`
- `src/config_validation.py`
- `src/data_adapters/yahoo_adapter.py`
- `src/dashboard.py`
- `tests/test_config_validation.py`
- `tests/test_yahoo_adapter.py`

### Files Not To Touch

- Broker/execution modules; none should be added.
- Thailand reference data files unless only adding comments/docs.
- DR fair value data files.
- Test fixtures that imply real market data unless already fake/demo.

### Implementation Tasks

- Ensure `config/data_sources.yaml` has a clear Yahoo example with `active_source: yahoo`.
- Add helper validation for Yahoo ticker list, period/start/end, interval, cache directory, cache TTL, and fallback-to-cache behavior.
- Add warnings when Yahoo tickers are missing.
- Add warnings when Yahoo returns partial data or missing tickers.
- Add dashboard controls for refresh/cache behavior by passing options, not editing constants.
- Keep CSV config available as fallback.

### Safety Rules

- Do not hardcode real ticker mappings unless they already exist in verified config/reference files.
- Do not call Yahoo in tests.
- Do not add API keys or realtime options.

### Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_config_validation.py tests\test_yahoo_adapter.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

Validation tests cover good config, missing tickers, invalid interval, invalid cache settings, and partial-data warnings using mocks/fake data.

### Rollback Notes

Revert config validation and dashboard control changes together. Keep any added tests only if they still describe current behavior.

### Definition Of Done

- Yahoo config example is clear.
- Invalid Yahoo config produces actionable warnings/errors.
- Dashboard can control cache/refresh behavior through config/options.
- Existing CSV fallback remains intact.

### Recommended Commit Message

`Add Yahoo-first config validation workflow`

## Phase 6C: Universe/Ticker Management

### Goal

Use local reference-driven universe selection to generate Yahoo ticker lists where possible, without inventing ticker mappings.

### Files Likely To Change

- `config/thailand_universe.yaml`
- `config/data_sources.yaml`
- `src/reference_data.py`
- `src/thailand_reference.py`
- `src/config_validation.py`
- `src/dashboard.py`
- `tests/test_reference_data.py`
- `tests/test_thailand_reference.py`
- New focused tests for Yahoo ticker generation helpers

### Files Not To Touch

- Generated caches.
- DR fair-value input values.
- Any secrets or credentials.
- Source files unrelated to reference/ticker generation.

### Implementation Tasks

- Add local reference fields for Yahoo ticker symbols where verified by user-supplied local files.
- Add helper to select a universe and emit a Yahoo ticker list from local reference data.
- Add warnings when a selected ticker lacks Yahoo format.
- Preserve Thailand domestic breadth exclusions for DR/DRx/ETF/DW/warrants/suspended/illiquid rows.
- Keep DR signal generation based on underlying instruments and DR execution quality based on local DR data.
- Document that missing Yahoo ticker format means the ticker is skipped for Yahoo loading.

### Safety Rules

- Do not invent Thai-to-Yahoo suffix mappings.
- Do not infer DR underlying mappings from Yahoo names.
- Do not include DR/DRx in domestic Thailand breadth.
- Do not silently include unclassified securities.

### Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_reference_data.py tests\test_thailand_reference.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

Tests cover universe selection, missing Yahoo ticker warnings, domestic exclusion rules, and no invented mapping behavior.

### Rollback Notes

Revert ticker-generation helpers and reference schema additions together. Keep old local universe files valid if possible.

### Definition Of Done

- A selected local universe can produce a Yahoo ticker list where local Yahoo symbols exist.
- Missing symbols are reported.
- Domestic Thailand breadth exclusions still pass tests.
- No real mapping is invented.

### Recommended Commit Message

`Add local universe Yahoo ticker selection`

## Phase 6D: Yahoo Data Refresh And Cache Controls

### Goal

Add dashboard controls that make Yahoo refresh/cache behavior explicit and avoid repeated downloads on Streamlit reruns.

### Files Likely To Change

- `src/dashboard.py`
- `src/data_adapters/yahoo_adapter.py`
- `src/data_quality.py`
- Tests for cache metadata/helper behavior

### Files Not To Touch

- Manual upload parser except for UI placement.
- Broker/execution code; none should exist.
- Test files unrelated to Yahoo/cache behavior.

### Implementation Tasks

- Add a dashboard refresh button for Yahoo historical data.
- Display cache-first status.
- Display cache path and last updated timestamp.
- Add stale-cache warning based on configured TTL.
- Add fallback-to-cache warning when a live historical download fails and cache is used.
- Ensure Streamlit reruns do not repeatedly download data unless refresh is requested.

### Safety Rules

- Refresh means historical Yahoo download only, not realtime.
- Do not run network calls in tests.
- Do not store credentials.
- Do not delete cache automatically unless explicitly requested by user action.

### Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_yahoo_adapter.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

Tests cover cache metadata, stale warnings, fallback-to-cache warnings, and refresh flag behavior using mocks/fake cache files.

### Rollback Notes

Revert dashboard refresh controls and cache metadata helpers. Existing adapter cache-first behavior should remain usable.

### Definition Of Done

- User can see cache state before running research.
- User can explicitly refresh historical Yahoo data.
- Cache-first/fallback behavior is visible.
- Reruns do not trigger repeated downloads by default.

### Recommended Commit Message

`Add Yahoo cache refresh controls`

## Phase 6E: Backtest From Yahoo Historical Data

### Goal

Let the opt-in backtest use Yahoo-loaded historical prices through the existing configured pipeline.

### Files Likely To Change

- `src/dashboard.py`
- `src/topdown_pipeline.py`
- `src/backtest_integration.py`
- `src/data_quality.py`
- `tests/test_backtest_integration.py`
- Dashboard/report helper tests

### Files Not To Touch

- `src/backtest.py` unless a clear bug is found.
- Broker/execution code; none should be added.
- DR local quality data files.
- Manual upload fallback behavior.

### Implementation Tasks

- Ensure config/Yahoo mode can pass historical price data into existing backtest outputs.
- Keep backtest opt-in.
- Add dashboard backtest data coverage warnings for missing dates/tickers.
- Show that backtest uses historical data and research assumptions only.
- Preserve explicit signal table support for tests and advanced workflows.
- Keep DR backtest signals underlying-driven when DR mappings exist.

### Safety Rules

- Do not present backtest as a recommendation or guarantee.
- Do not add broker execution.
- Do not treat Yahoo as local execution-quality data.
- Do not mix DR/DRx into Thailand domestic breadth.

### Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_backtest.py tests\test_backtest_integration.py tests\test_backtest_dashboard_report.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

Backtest tests pass with mocked/fake Yahoo-loaded price tables and coverage warnings; full suite passes.

### Rollback Notes

Revert only the Yahoo-to-backtest integration surface. Standalone backtest and manual upload backtest behavior should remain.

### Definition Of Done

- Yahoo historical prices can feed the opt-in backtest path.
- Coverage warnings are visible.
- Backtest remains research assumptions only.
- No dashboard/report language implies trading advice.

### Recommended Commit Message

`Enable opt-in backtest from Yahoo historical data`

## Phase 6F: Documentation And Tests

### Goal

Document the Yahoo-first workflow and lock behavior with tests that do not call external network.

### Files Likely To Change

- `README.md`
- `PROJECT_STATUS.md`
- `RUN_STATE.md`
- `CODEX_WORKFLOW.md` if workflow commands need clarification
- `YAHOO_FIRST_WORKFLOW_PLAN.md`
- Focused test files added in phases 6A-6E

### Files Not To Touch

- Source code unless fixing documentation-discovered test failures.
- Secrets, `.env`, credentials, cookies, private keys.
- Generated caches.

### Implementation Tasks

- Update README with Yahoo-first setup, config mode, cache behavior, and manual upload fallback.
- Update `PROJECT_STATUS.md` with completed Phase 6 status only after implementation is complete.
- Update `RUN_STATE.md` with the next recommended prompt.
- Add or refine tests for dashboard helpers, config validation, cache behavior, and Yahoo-first workflow.
- Confirm tests use mocks/fake data and never call external network.

### Safety Rules

- Do not invent project status before implementation is complete.
- Do not include real secrets or private endpoints.
- Do not document unsupported realtime/broker capabilities.

### Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

Full suite passes with no network calls in tests.

### Rollback Notes

Documentation changes can be reverted independently if they overstate the implemented behavior.

### Definition Of Done

- README explains Yahoo-first operation and manual fallback.
- Status docs match implemented reality.
- Tests cover the Yahoo-first workflow.
- Future Codex sessions can continue with short prompts.

### Recommended Commit Message

`Document Yahoo-first workflow and tests`

## Cross-Phase Definition Of Done

The Yahoo-first transition is complete when:

1. Dashboard defaults to Config/Yahoo mode.
2. Manual upload remains available as Advanced/Fallback.
3. Yahoo historical status, cache status, and stale/fallback warnings are visible.
4. Local reference files remain the source for metadata, Thailand universe, DR/DRx mapping, sector/country maps, security type, and DR quality data.
5. Universe selection can generate Yahoo tickers only from verified local reference fields.
6. Backtest can use Yahoo historical prices through the existing opt-in pipeline.
7. All report/dashboard language says research signal or research assumption only.
8. Tests pass without external network calls.
