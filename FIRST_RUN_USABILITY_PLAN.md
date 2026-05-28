# First-Run Usability Plan

## Objective

Make the Yahoo-first dashboard usable on a fresh checkout without requiring the user to understand internal adapter/reference-data failures first.

## Implementation Status

Phases 7A through 7F are complete.

Implemented behavior:
- Dashboard reports `yfinance` availability and shows exact virtual-environment install/run commands when missing.
- Config source mode can explicitly map missing local reference paths to bundled fake/demo sample files at runtime only.
- Dashboard shows a Yahoo startup checklist before configured loading, with blockers, warnings, cache status, reference coverage, demo mode state, and manual upload fallback status.
- Dashboard has an explicit Yahoo historical smoke-test button using configured tickers and cache-first behavior.
- Dashboard reports production reference readiness, including missing files, required columns, sample-file warnings, and local Yahoo ticker fields.
- Documentation covers first-run commands, demo vs production reference mode, Yahoo historical/cache limitations, manual upload fallback, common first-run errors, and known pytest cache warning.
- Tests use mocks/fake data and do not call Yahoo or external network services.

Remaining responsibility:
- Replace fake/demo sample reference files with manually verified local data before production research use.
- Keep Yahoo historical/cache-based only and keep local reference files as the source of truth for metadata, Thailand universe membership, DR/DRx mapping, security type, sector/country maps, and local DR quality data.

The original first-run problem was that `active_source: yahoo` was visible as the default path, but a fresh run could fail with raw or confusing errors:

- `No module named 'yfinance'`
- missing local reference files:
  - `data/reference/metadata.csv`
  - `data/reference/sector_map.csv`
  - `data/reference/country_map.csv`

Yahoo/yfinance can provide historical OHLCV prices only. It cannot provide authoritative metadata, sector/country maps, Thailand universe membership, DR/DRx mappings, security types, suspended flags, local liquidity, bid/ask spreads, fair-value inputs, or local DR quality data. The first-run experience must make that boundary clear while still giving the user a working safe path.

## Global Safety Rules

- No live trading.
- No broker integration.
- No scraping.
- No API keys.
- No realtime data.
- No buy/sell recommendations.
- Do not remove manual upload fallback.
- Do not weaken or delete tests.
- Keep outputs as research signals or research assumptions only.
- Do not hide missing production reference data.
- Demo/sample data must be clearly labeled as fake/demo/sample data.
- Do not infer or invent ticker mappings, sector classifications, security types, countries, DR mappings, prices, liquidity, spreads, fair values, or production reference data.

## Design Principles

- The dashboard should start with diagnostics, not a crash.
- A user should know whether the blocker is environment, Yahoo/cache, config, or local reference data.
- Demo mode can make the app runnable, but must never appear production-ready.
- Production mode should preserve strict missing-reference reporting.
- Tests for all first-run helpers must use mocks/fake data only and must not call Yahoo or any external network.

## Phase 7A: First-Run Environment And Dependency Diagnostics

### Goal

Detect whether `yfinance` is importable in the same Python environment running Streamlit and show an actionable fix before the Yahoo adapter raises a raw import exception.

### Files Likely To Change

- `src/dashboard.py`
- `src/config_validation.py` or a new focused helper such as `src/startup_diagnostics.py`
- `tests/test_dashboard_yahoo_first.py` or new `tests/test_startup_diagnostics.py`
- `README.md` only if the fix command needs first-run documentation

### Files Not To Touch

- `src/backtest.py`
- Broker/execution modules; none should be added.
- `.env`, secrets, tokens, credentials, cookies, private keys
- Generated Yahoo cache files
- Production reference data values

### Implementation Tasks

- Add a helper that checks import availability with `importlib.util.find_spec("yfinance")` or equivalent.
- Make the helper pure and mockable so tests do not import or install packages.
- In dashboard Config/Yahoo mode, show a clear status row:
  - `yfinance available`
  - `yfinance missing`
- If missing, show this exact fix command:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

- Prevent the first-run display from degrading into a raw `No module named 'yfinance'` exception.
- Keep non-Yahoo sources unaffected.
- Keep Yahoo historical/cache behavior unchanged when dependency is available.

### Safety Rules

- Do not auto-install packages from the dashboard.
- Do not make network calls from diagnostics.
- Do not hide missing local reference files after environment diagnostics pass.
- Do not claim Yahoo is realtime or complete.

### Exact Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

If a new focused test file is created:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_startup_diagnostics.py --basetemp=tmp_pytest
```

### Expected Test Result

All tests pass. New tests verify yfinance-present and yfinance-missing states using mocks only, with no external network calls and no package installation.

### Rollback Notes

Revert the diagnostics helper and dashboard display changes. The existing Yahoo adapter behavior should remain usable, though less friendly, after rollback.

### Definition Of Done

- Dashboard shows yfinance availability before attempting Yahoo load.
- Missing dependency produces the exact fix command.
- Raw `No module named 'yfinance'` is not the primary first-run user experience.
- Tests cover dependency-present and dependency-missing paths with mocks.

### Recommended Commit Message

`Add Yahoo first-run dependency diagnostics`

## Phase 7B: Demo Reference Bootstrap / Sample Reference Mode

### Goal

Add a safe demo reference mode that maps bundled sample files to required local reference inputs, making first run demonstrable without pretending sample data is production data.

### Files Likely To Change

- `config/data_sources.yaml`
- `src/dashboard.py`
- `src/config_validation.py`
- `src/reference_data.py` only if path-resolution helpers are needed
- `tests/test_config_validation.py`
- `tests/test_dashboard_yahoo_first.py`
- `README.md`

### Files Not To Touch

- `src/data_adapters/yahoo_adapter.py` unless reference path handling must be adapter-aware
- `src/backtest.py`
- Broker/execution code; none should be added.
- Real production reference data values
- Secrets or credentials

### Implementation Tasks

- Add an explicit dashboard control such as `Use bundled fake/demo reference files`.
- Keep it off or clearly marked if production mode is selected.
- When enabled, map missing reference paths to bundled fake/demo files where schemas are compatible:
  - metadata
  - sector map
  - country map
  - asset map if needed
  - DR mapping if needed
  - Thailand sample reference files where relevant
- Show a persistent warning: `Demo reference files are fake/sample data and are not suitable for production research.`
- Keep production reference paths supported and visible.
- If production paths are missing and demo mode is off, report missing files clearly.
- Preserve Advanced/Fallback manual upload workflow.
- Avoid silently changing config files when a user toggles demo mode; pass runtime options or use a copied config object.

### Safety Rules

- Demo mode must never be labeled as production-ready.
- Do not invent missing production metadata.
- Do not infer Yahoo ticker mappings from local ticker names.
- Do not mix DR/DRx into Thailand domestic breadth.
- Do not remove strict production missing-file warnings.

### Exact Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_config_validation.py tests\test_dashboard_yahoo_first.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

All tests pass. Tests cover:

- production missing references are still reported
- demo reference mode maps known bundled sample files
- demo mode emits clear fake/sample warnings
- manual upload fallback remains available

### Rollback Notes

Revert demo-mode mapping and dashboard controls. Existing configured reference paths and manual upload fallback should remain intact.

### Definition Of Done

- A fresh user can opt into fake/demo reference files from the dashboard.
- Missing production reference data is not hidden.
- Demo mode is visibly labeled as fake/sample.
- Manual upload remains available.

### Recommended Commit Message

`Add demo reference bootstrap mode`

## Phase 7C: Yahoo-First Startup Checklist

### Goal

Show a clear startup checklist in the dashboard so the user knows exactly what is configured, what is available, and what blocks the run.

### Files Likely To Change

- `src/dashboard.py`
- `src/config_validation.py` or new `src/startup_diagnostics.py`
- `src/data_quality.py` if existing report helpers are extended
- `tests/test_dashboard_yahoo_first.py`
- `tests/test_config_validation.py` or new `tests/test_startup_diagnostics.py`

### Files Not To Touch

- `src/backtest.py`
- Broker/execution modules
- Generated cache files
- Production reference data values
- Secrets or credentials

### Implementation Tasks

- Build a pure helper that returns startup checklist rows for display and testing.
- Include:
  - `active_source`
  - yfinance availability
  - configured tickers
  - cache directory
  - cache file path and cache existence when adapter can be built
  - reference file coverage
  - missing reference files
  - whether demo sample fallback is enabled
  - whether manual upload fallback is available
- Display checklist before running the expensive pipeline.
- Separate blockers from warnings:
  - blockers: missing `yfinance` for Yahoo mode, no configured tickers, no cache and Yahoo load unavailable, missing required production references when demo mode is off
  - warnings: stale cache, partial reference coverage, demo mode enabled, optional local DR quality files missing
- Keep wording specific: `Yahoo historical OHLCV only`, `local reference required`, `research signals only`.

### Safety Rules

- Do not suppress missing production references.
- Do not use checklist status to invent defaults.
- Do not make network calls from the checklist helper.
- Do not remove manual upload fallback.

### Exact Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_config_validation.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

If a new focused test file is created:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_startup_diagnostics.py --basetemp=tmp_pytest
```

### Expected Test Result

All tests pass. Tests verify checklist rows for healthy config, missing yfinance, missing references, demo mode enabled, and empty ticker config using mocks/fake paths only.

### Rollback Notes

Revert checklist helper and dashboard display. Existing config validation warnings remain the fallback user guidance.

### Definition Of Done

- Dashboard shows a first-run checklist before pipeline execution.
- User can tell exactly what blocks a run.
- Checklist distinguishes production missing references from demo fallback.
- Tests cover checklist states without network calls.

### Recommended Commit Message

`Add Yahoo startup checklist`

## Phase 7D: One-Click Yahoo Smoke Test

### Goal

Add a controlled Yahoo smoke test button using configured tickers and cache-first behavior, so the user can verify historical Yahoo loading without triggering repeated downloads on Streamlit reruns.

### Files Likely To Change

- `src/dashboard.py`
- `src/data_adapters/yahoo_adapter.py` only if a small cache-aware smoke-test helper is needed
- `src/startup_diagnostics.py` if created in earlier phases
- `tests/test_dashboard_yahoo_first.py`
- `tests/test_yahoo_adapter.py`

### Files Not To Touch

- `src/backtest.py`
- Broker/execution modules
- Manual upload parser except for preserving fallback display
- Secrets or credentials
- Production reference data values

### Implementation Tasks

- Add a dashboard button such as `Run Yahoo historical smoke test`.
- Use configured tickers and current Yahoo runtime options.
- Use cache-first behavior by default.
- Avoid repeated downloads on rerun by caching the smoke-test result by config/cache token.
- Limit displayed output to:
  - attempted tickers
  - rows loaded
  - date range
  - missing/partial ticker warnings
  - cache/fallback status
- If yfinance is missing, show the Phase 7A fix command instead of attempting the smoke test.
- If no tickers are configured, report that as a blocker.

### Safety Rules

- Smoke test is historical Yahoo loading only, not realtime.
- Do not call Yahoo in tests.
- Do not add API keys, scraping, broker integration, or live trading.
- Do not auto-refresh repeatedly on Streamlit reruns.
- Do not present smoke-test success as data completeness or research validity.

### Exact Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_dashboard_yahoo_first.py tests\test_yahoo_adapter.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

All tests pass. Tests use fake adapters/mocks to cover:

- cache-first smoke-test success
- yfinance missing blocker
- empty ticker blocker
- partial ticker warning
- no repeated load for unchanged smoke-test cache key

### Rollback Notes

Revert smoke-test button/helper and tests. Core Yahoo loading and dashboard config source workflow should remain unchanged.

### Definition Of Done

- User can run one explicit historical Yahoo smoke test.
- Reruns do not repeatedly download.
- Smoke-test result is clearly limited to historical loading diagnostics.
- Tests do not call external network.

### Recommended Commit Message

`Add Yahoo smoke test control`

## Phase 7E: Production Reference Readiness

### Goal

Document and validate what must be replaced before production research use, without inventing mappings or classifications.

### Files Likely To Change

- `README.md`
- `PROJECT_STATUS.md`
- `RUN_STATE.md`
- `PHASE_PLAN.md`
- `config/data_sources.yaml` comments only if useful
- `src/config_validation.py`
- `src/thailand_reference.py`
- `tests/test_config_validation.py`
- `tests/test_thailand_reference.py`

### Files Not To Touch

- Generated cache files
- Broker/execution code
- Secrets or credentials
- Source modules unrelated to reference validation
- Real reference data values unless explicitly supplied and verified by the user

### Implementation Tasks

- Add a production reference readiness checklist covering:
  - metadata file
  - sector map
  - country map
  - asset map
  - Thailand universe
  - Thailand sector map
  - Thailand security types
  - Thailand liquidity
  - Thailand DR/DRx mapping
  - DR market data
  - DR bid/ask
  - fair value inputs
  - FX rates
  - underlying prices
- Validate required columns and report missing columns clearly.
- Document optional vs required reference files by dashboard layer.
- Add warnings that fake/demo bundled files are not production research data.
- Keep local reference files as source of truth for metadata and mappings.
- Do not infer Thai Yahoo suffixes, DR underlyings, sectors, countries, or security types.

### Safety Rules

- Do not invent production values.
- Do not silently fill missing classification fields.
- Do not hide missing production references behind demo mode.
- Do not treat Yahoo metadata as authoritative.
- Keep outputs as research signals only.

### Exact Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest tests\test_config_validation.py tests\test_thailand_reference.py tests\test_reference_data.py --basetemp=tmp_pytest
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

All tests pass. New or updated tests verify required-column validation, missing-file reporting, fake/demo warnings, and no-inferred-mapping behavior.

### Rollback Notes

Revert readiness docs and validation additions. Existing config/reference validation should continue to work.

### Definition Of Done

- User has a clear checklist for replacing demo data with verified production files.
- Required columns are validated.
- Missing production data is visible.
- No mappings or classifications are inferred.

### Recommended Commit Message

`Document production reference readiness`

## Phase 7F: Final Docs And Regression Tests

### Goal

Finalize the first-run usability workflow documentation and lock behavior with tests.

### Files Likely To Change

- `README.md`
- `PROJECT_STATUS.md`
- `RUN_STATE.md`
- `PHASE_PLAN.md`
- `FIRST_RUN_USABILITY_PLAN.md`
- Focused tests added in Phases 7A-7E

### Files Not To Touch

- Source code unless fixing a small documentation-discovered bug
- Secrets, `.env`, tokens, credentials, cookies, private keys
- Generated caches
- Broker/execution modules

### Implementation Tasks

- Update README with:
  - first-run install command
  - dashboard startup checklist explanation
  - demo reference mode warning
  - production reference readiness checklist
  - Yahoo smoke test usage
  - manual upload fallback instructions
- Update `PROJECT_STATUS.md` with completed Phase 7 status only after implementation is complete.
- Update `RUN_STATE.md` with the next recommended prompt.
- Update `PHASE_PLAN.md` to move from first-run usability to the next approved maintenance/data-readiness work.
- Confirm all tests use mocks/fake data and never call external network services.
- Run the full test suite.

### Safety Rules

- Do not claim first-run demo mode is production-ready.
- Do not document realtime, broker, scraping, API-key, or advice capabilities.
- Do not delete manual upload fallback.
- Do not weaken tests to make docs pass.

### Exact Test Commands

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest
```

### Expected Test Result

Full suite passes. Any known Windows `.pytest_cache` warning is documented and does not affect pass/fail status.

### Rollback Notes

Documentation-only changes can be reverted independently. If source changes were required for final regression fixes, revert them with their focused tests.

### Definition Of Done

- README explains first-run Yahoo setup, dependency diagnostics, demo references, smoke test, and production reference readiness.
- Status docs match implemented behavior.
- Regression tests cover first-run UX helpers.
- Full test suite passes with no external network calls.

### Recommended Commit Message

`Finalize first-run usability docs and tests`

## Cross-Phase Definition Of Done

First-run usability is complete when:

1. A missing `yfinance` dependency produces an actionable dashboard message and exact install/run commands.
2. The dashboard can show a startup checklist before attempting the full pipeline.
3. Missing production reference files are visible and not hidden.
4. A clearly labeled fake/demo reference mode can make the app demonstrable without manual upload.
5. Manual upload remains available as fallback.
6. Yahoo remains historical/cache-based only.
7. A one-click Yahoo historical smoke test is available and rerun-safe.
8. Production reference readiness docs explain exactly what must be verified and replaced.
9. Tests cover first-run helpers with mocks/fake data only and no external network calls.
