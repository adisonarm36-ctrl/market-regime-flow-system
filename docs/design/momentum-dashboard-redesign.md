# Momentum Dashboard Redesign Plan

## 1. Current Repo Understanding

### Current relevant files and folders found

- `app.py`: small entry point that imports and runs `src.dashboard.main`.
- `src/dashboard.py`: Streamlit dashboard UI, source selection, Yahoo diagnostics, manual upload fallback, page navigation, status tables, backtest display, and daily report display.
- `src/topdown_pipeline.py`: orchestrates the research pipeline and returns report-ready `pandas.DataFrame` outputs.
- `src/momentum.py`: momentum calculations used by the pipeline.
- `src/stock_selection.py`: research candidate ranking from metadata, momentum, breadth, clusters, redundancy, and DR quality.
- `src/report_generator.py`: narrative daily report text plus CSV and HTML export helpers.
- `src/backtest.py`: core backtest calculations and metrics.
- `src/backtest_integration.py`: converts pipeline stock-ranking outputs into backtest signal tables and builds backtest data coverage warnings.
- `tests/test_dashboard_yahoo_first.py`: dashboard helper and Yahoo-first diagnostics tests.
- `tests/test_report_generator.py`: report narrative and CSV/HTML export tests.
- `tests/test_backtest.py`: core backtest calculation tests.
- `tests/test_backtest_integration.py`: pipeline/backtest integration and coverage warning tests.
- `tests/test_backtest_dashboard_report.py`: dashboard/report helper tests for backtest output tables and CSV export.
- `requirements.txt`: `pandas`, `numpy`, `scipy`, `scikit-learn`, `networkx`, `plotly`, `streamlit`, `pyyaml`, `pytest`, `yfinance`.
- `data/sample/` and `data/reference/`: fake/demo sample data and fake/demo reference data for smoke testing.
- `config/`: YAML configuration for data sources, universes, maps, thresholds, and DR mappings.
- No existing `docs/` or `specs/` directory was found during repo file inspection. This document creates `docs/design/` because the requested path is explicit and no conflicting docs convention exists.

### Current branch/context

- Current branch for this document: `docs-momentum-dashboard-redesign-plan`.
- The repo is a top-down market research system. It must output research signals only, not financial advice, buy/sell recommendations, or guaranteed outcomes.
- Yahoo/yfinance is historical/cache-based only. It is not realtime and is not the source of truth for metadata, sectors, countries, Thailand universe membership, DR mappings, or execution quality data.

### Existing dashboard/report/export/backtest pieces

- Dashboard:
  - Implemented in Streamlit in `src/dashboard.py`.
  - Uses a sidebar with `Config source` as default and `Advanced / fallback manual upload` for CSV uploads.
  - Includes Yahoo dependency diagnostics, startup checklist, demo reference mode, production reference readiness, cache status, cache refresh controls, and a Yahoo historical smoke-test button.
  - Shows pages for global flow, country health, Thailand market health, Thailand reference status, sector breadth, clusters, stock ranking, DR global proxy, redundancy, backtest, and daily report.
  - Uses mostly `st.dataframe`, `st.warning`, `st.info`, `st.success`, tabs, and sidebar controls.
- Report/export:
  - `src/report_generator.py` builds narrative daily report sections from output tables.
  - Current confirmed export formats are CSV and HTML.
  - Markdown and PDF export are not confirmed in the inspected implementation.
- Backtest:
  - Backtests are opt-in research assumptions.
  - `src/backtest.py` calculates portfolio, positions, instrument returns, metrics, instrument metrics, and warnings.
  - Current confirmed metrics include `total_return`, `annualized_volatility`, `max_drawdown`, `hit_rate`, `turnover`, `average_gross_exposure`, `observations`, and `signal_type`.
  - `src/backtest_integration.py` builds pipeline signals and coverage warnings.
  - Backtest language already includes "research signal only" and "not financial advice" safeguards.

### Unknowns and assumptions

- Unknown / needs inspection: whether any separate frontend besides Streamlit is actively used. Root files `index.html`, `app.js`, `styles.css`, and `sample-data.js` exist, but the active Python app path appears to be Streamlit via `app.py`.
- Unknown / needs inspection: whether a watchlist feature exists. No watchlist module was identified from the file list.
- Unknown / needs inspection: whether PDF export exists. CSV and HTML exports are confirmed; PDF is not.
- Unknown / needs inspection: whether Markdown export exists. CSV and HTML exports are confirmed; Markdown is not.
- Unknown / needs inspection: exact production data field coverage in user-supplied files.
- Assumption: "Momentum Project dashboard" refers to the existing market-regime-flow Streamlit dashboard and its momentum/stock-ranking outputs, not a separate app.
- Assumption: Any implementation work following this plan must preserve existing strategy, pipeline, backtest, and export behavior unless explicitly approved later.

## 2. Design Goal

The product should become a Decision Dashboard, not a raw metrics browser. It should help the user quickly answer:

- Today, what should I review?
- Why did this signal appear?
- How strong is the evidence?
- What risks/data-quality warnings exist?
- What can I export/share?

The dashboard should organize existing research outputs into an explainable review workflow. It should not change the signal calculations, backtest calculations, data adapters, or export behavior during UX redesign phases unless a later task explicitly authorizes that work.

## 3. UX Principles

- Mobile-first: the primary review path should work on narrow screens without horizontal table scanning.
- Fast scanning: show the most important review items first, with progressive detail below.
- Explainable signals: every highlighted signal should show the metrics or source rows that caused it.
- Separate Fact / Assumption / Recommendation:
  - Fact: observed historical data or calculated metric.
  - Assumption: configured backtest assumption or threshold.
  - Recommendation: avoid recommendation language; use "review", "watch", "signal", and "research candidate" instead.
- No buy/sell advice: never label outputs as investment advice, trade instructions, guaranteed opportunities, or buy/sell calls.
- Preserve existing strategy/backtest logic: UI phases should consume current pipeline outputs without changing calculations.
- Do not overload the user with raw metrics: default views should summarize, with raw tables available in expandable sections.
- Make confidence and data quality visible: incomplete metadata, missing reference files, low sample size, stale cache, skipped layers, and demo data must be visible.

## 4. Target Information Architecture

### Today Decision Hub

The first screen after data is loaded. It summarizes market regime, top signals, risk alerts, strategy health, data freshness, and quick actions. It should be the default review page.

### Signal Explorer

A searchable, filterable list of research candidates. It should replace wide ranking tables on mobile with stacked signal cards and compact filter controls.

### Signal Detail Drawer/Page

A focused detail view for one ticker or instrument. It should explain why the signal exists, what data supports it, what is missing, and what risks apply.

### Backtest Evidence View

A plain-language evidence view for opt-in backtest outputs. It should show calculated metrics only when they already exist and display clear limitations.

### Data Quality & Risk Warnings

A central warning surface for missing metadata, stale caches, demo references, skipped layers, missing DR data, Thailand eligibility exclusions, and backtest coverage warnings.

### Report Export View

A narrative report builder/review screen that shows the sections that will be exported. It should support only confirmed export formats by default: CSV and HTML.

## 5. Today Decision Hub Design

### Market Regime Card

- Purpose: tell the user the current high-level market condition before reviewing individual signals.
- Inputs/data needed:
  - `global_flow_summary`
  - `country_breadth_summary`
  - `thailand_market_health`
  - `sector_breadth_summary`
  - `pipeline_layer_status` and `warnings`
- UI content:
  - Dominant regime label, such as strongest available country/market regime.
  - Key supporting metric rows: breadth score, flow score, percent above moving averages where available.
  - Short "Why" text grounded in existing metrics.
  - Research-signal disclaimer.
- Empty state:
  - "Market regime not available. Needs price data and breadth inputs."
- Error state:
  - "Market regime skipped because required layer failed. See Data Quality & Risk Warnings."
- Mobile behavior:
  - Single full-width card with two to four stacked metric rows.
  - Raw supporting table hidden behind a collapsible section.
- Test/verification checklist:
  - Shows available metric names and values.
  - Does not claim real money flow unless actual fund flow data exists.
  - Displays empty state when outputs are missing or empty.
  - Does not use buy/sell language.

### Top Signals Card

- Purpose: identify the highest-priority research candidates for review today.
- Inputs/data needed:
  - `stock_ranking`
  - `momentum_summary`
  - optional metadata columns from merged reference data
  - `sector_breadth_summary`
  - `redundancy_report`
- UI content:
  - Top 3 to 5 signal cards.
  - Symbol, name if available, sector/industry if available, momentum or research score, confidence, badges, and "Why this signal?"
  - Link/action to Signal Explorer and detail view.
- Empty state:
  - "No research candidates available. Needs metadata, momentum, and ranking outputs."
- Error state:
  - "Signal ranking skipped. See pipeline warnings."
- Mobile behavior:
  - Vertical card stack.
  - Do not render a wide ranking table as the primary mobile view.
- Test/verification checklist:
  - Handles missing name/sector/industry as "Not available".
  - Hides or marks unavailable metrics without inventing values.
  - Keeps failed-filter signals visibly separated or excluded according to existing output semantics.

### Risk Alerts Card

- Purpose: surface warnings that should change how the user interprets signals.
- Inputs/data needed:
  - `warnings`
  - `backtest_warnings`
  - `pipeline_layer_status`
  - `data_quality_report`
  - `reference_data_report`
  - Thailand and DR quality status tables
- UI content:
  - Top critical warnings by category: data, reference, cache, backtest, DR quality, demo mode.
  - Count of warnings by severity if severity is available; otherwise plain grouped list.
- Empty state:
  - "No warnings reported by current outputs."
- Error state:
  - "Warning status unavailable. Check pipeline layer status."
- Mobile behavior:
  - Collapsible grouped warning list.
  - Show only first few warnings by default.
- Test/verification checklist:
  - Demo/sample data warning remains visible.
  - Missing production reference warnings remain visible.
  - No raw tracebacks shown for user-facing optional data issues.

### Strategy Health Card

- Purpose: show whether the research workflow produced enough evidence to review signals.
- Inputs/data needed:
  - `pipeline_layer_status`
  - `stock_ranking`
  - `momentum_summary`
  - `cluster_summary`
  - `redundancy_report`
  - optional backtest outputs
- UI content:
  - Layers available / limited / skipped.
  - Number of candidates, number of filtered or redundant instruments if available.
  - Backtest enabled/disabled status.
- Empty state:
  - "Strategy health unavailable until pipeline outputs exist."
- Error state:
  - "One or more strategy layers failed. See warnings."
- Mobile behavior:
  - Compact status chips: Available, Limited, Skipped.
  - Details in collapsible rows.
- Test/verification checklist:
  - Does not alter filtering/backtest logic.
  - Shows skipped layers clearly.
  - Backtest status says "research assumptions only".

### Data Freshness Card

- Purpose: show whether the data source is current enough for review.
- Inputs/data needed:
  - Yahoo cache metadata where applicable.
  - OHLCV date range from loaded prices.
  - Startup checklist and smoke-test result if available.
- UI content:
  - Source mode.
  - Latest available price date if available.
  - Cache path/status/last updated for Yahoo.
  - Demo/reference mode state.
- Empty state:
  - "Freshness unavailable. Needs loaded price data or cache metadata."
- Error state:
  - "Data freshness check failed. Use manual upload fallback or inspect source settings."
- Mobile behavior:
  - Small metric list; avoid full cache metadata object display.
- Test/verification checklist:
  - Yahoo is labeled historical/cache-based only.
  - Stale cache warnings remain visible.
  - Missing production reference warnings are not hidden by demo mode.

### Quick Actions Card

- Purpose: give the user direct next steps without hunting through tabs.
- Inputs/data needed:
  - Current outputs and available export functions.
  - Data source state and page routing state.
- UI content:
  - Run Yahoo historical smoke test if source is Yahoo.
  - Open Signal Explorer.
  - Open Data Quality & Risk Warnings.
  - Open Report Export View.
  - Download/export where supported by existing implementation.
- Empty state:
  - "Actions unavailable until data source is configured or uploaded."
- Error state:
  - "Some actions are unavailable because required outputs are missing."
- Mobile behavior:
  - Large thumb-friendly buttons stacked vertically.
- Test/verification checklist:
  - Does not trigger network downloads on rerun unless user explicitly refreshes.
  - Export actions only appear for confirmed supported formats.
  - Manual upload fallback remains reachable.

## 6. Signal Card Design

### Card fields

- Symbol: from `Ticker` or equivalent output column.
- Name if available: show "Not available" when missing.
- Sector/industry if available: show "Not available" when missing.
- Momentum Score: use existing momentum or research score fields only. Do not create a new calculation unless approved.
- Trend Status: derive only from existing output fields if present; otherwise "Not available".
- Relative Strength: use existing flow, momentum, or benchmark-relative fields only if present; otherwise "Not available".
- Risk Level: use existing volatility, failed filters, drawdown, data-quality, or warning fields if present; otherwise "Needs data source".
- Confidence Level: use existing confidence fields when present; otherwise infer only from data availability labels, not from market outcome expectations.
- Last Updated: use loaded price date or cache timestamp if available.
- Badge list: derived from existing output columns and explicit data availability.
- Short "Why this signal?" explanation: metric-backed text using current score, trend, sector, breadth, redundancy, and warning fields.
- Actions:
  - View Detail.
  - Compare.
  - Export/Add to report if available.

### Recommended badges

- Strong Momentum: high existing momentum/research score threshold, if threshold is defined.
- Early Signal: only if existing trend/momentum fields support this label; otherwise mark as future enhancement.
- Overextended: only if existing distance-from-high, volatility, or similar metric supports it.
- Low Data Confidence: missing metadata, stale data, partial price coverage, demo sample, or skipped layer.
- Backtest Supported: backtest output exists for this signal or underlying setup; otherwise "Backtest not available".
- Sector Leader: sector/industry context exists and current output supports ranking.
- Watchlist: future enhancement unless a watchlist feature is confirmed.

## 7. Signal Detail View Design

### Decision Summary

- Show symbol, name, sector/industry, current signal label, score, confidence, and key warnings.
- Use "Review" or "Research signal" language, not buy/sell language.
- If fields are missing, display "Not available" or "Needs data source".

### Price/indicator chart area

- Show price and available indicators from existing data only.
- Do not calculate new indicators in the UI phase unless approved.
- If price history is missing, show "Needs price data".

### Signal Breakdown

- Break down existing metrics contributing to the signal:
  - momentum metrics
  - breadth context
  - redundancy status
  - failed filters
  - DR quality if applicable
- Link each explanation to the source table or column where possible.

### Relative Strength vs sector/benchmark

- Use existing benchmark-relative or sector-relative outputs if available.
- If unavailable, show "Not available" rather than creating a new calculation in the UI.

### Volume confirmation

- Use existing volume z-score or volume-related fields if available.
- If unavailable, show "Needs volume data".

### Volatility/risk warning

- Use existing volatility, drawdown, failed-filter, data-quality, or warning outputs.
- Keep risk labels descriptive, not predictive.

### Backtest evidence

- Show opt-in backtest outputs only when already calculated.
- Display research-assumption labels prominently.
- For DRs, keep signal evidence tied to the underlying when existing logic does so.

### Data quality

- Show data source, last updated date, missing metadata, skipped layers, stale cache, demo/reference warnings, and any ticker-specific warnings.

### Export/report actions

- Add this signal to a report only if report composition support exists or is implemented in a later approved phase.
- Existing confirmed exports are CSV and HTML.

## 8. Backtest Evidence UX

Show only metrics already calculated by `src/backtest.py` or present in current pipeline outputs:

- Similar setup count: Unknown / needs inspection. Do not display unless implemented.
- Win rate if already calculated: current metric appears to be `hit_rate`; label clearly as historical hit rate.
- Average return if already calculated: Unknown / needs inspection. Current confirmed metric is `total_return`; average return may require additional inspection or future approved calculation.
- Max drawdown if already calculated: current metric `max_drawdown`.
- Date range if available: derive from backtest portfolio index only if present in output.
- Sample size warning: use `observations` and `backtest_warnings` where available.
- Data limitations:
  - missing common dates
  - missing common tickers
  - missing price tickers
  - missing signal tickers
  - Yahoo historical/cache limitations
  - demo/sample reference limitations

Rules:

- No fabricated metrics.
- No implied future performance.
- No recommendation language.
- Every metric should include a plain-language explanation and the source output field.

## 9. Report Export Design

### Narrative report structure

- Market Summary:
  - global flow proxy
  - country/Thailand regime
  - sector breadth
- Top Opportunities / Top Signals:
  - use "Top Signals" as the preferred label to avoid advice language.
  - include score, reason, confidence, and warnings.
- Key Risks:
  - market, data quality, stale cache, demo/reference, backtest coverage, DR quality.
- Backtest Evidence:
  - opt-in backtest assumptions only.
  - calculated metrics and limitations.
- Data Quality Notes:
  - missing metadata/reference data.
  - skipped layers.
  - sample/demo status.
- Watchlist for Next Review:
  - future enhancement unless a watchlist feature is confirmed.
- Appendix / Raw Data:
  - raw output tables and exports.

### Supported export formats

- CSV: confirmed by `export_report_to_csv`.
- HTML: confirmed by `export_report_to_html`.
- Markdown: potential future enhancement; not confirmed in current implementation.
- PDF: potential future enhancement; not confirmed in current implementation.

Do not remove existing export formats. Do not change export implementation behavior during design-only or UI-only phases unless explicitly approved.

## 10. Mobile-First Behavior

- Replace wide tables with stacked cards on mobile.
- Avoid horizontal scrolling where possible.
- Use collapsible sections for raw tables, long warning lists, and advanced diagnostics.
- Keep primary actions thumb-friendly, especially:
  - View Detail
  - Open Signal Explorer
  - Run Smoke Test
  - Export Report
- Lazy-load heavy charts/tables if needed.
- Avoid creating too many chart objects at once.
- Prefer summary cards first, raw data second.
- Keep navigation shallow: the first screen should answer what to review today.

## 11. Accessibility and Readability

- Do not rely on color alone.
- Use labels, icons, and badges together where possible.
- Maintain good contrast for status, risk, warning, and confidence states.
- Use clear empty states and error states.
- Explain metrics in human-readable language.
- Keep table column labels readable.
- Keep warning text direct and actionable.
- Avoid dense paragraphs inside cards.
- Ensure all actions have explicit labels.

## 12. Performance Notes

- Avoid expensive rendering loops in Streamlit reruns.
- Avoid unnecessary chart re-renders.
- Paginate or virtualize large signal lists if needed.
- Avoid creating many objects repeatedly in client-side loops.
- Keep mobile FPS smooth by limiting simultaneous heavy charts.
- Cache derived values where safe and where existing behavior supports caching.
- Do not change calculation logic without explicit approval.
- Do not trigger Yahoo downloads on rerun unless the user explicitly requests refresh.
- Prefer summary DataFrames for dashboard views and keep raw tables collapsed by default.

## 13. Implementation Phases

Each phase must be small, testable, and verified before moving to the next phase.

### Phase 0: Baseline Inspection

- Goal: confirm current UI behavior, outputs, supported export formats, and test/build commands.
- Must do:
  - Run `git status --short`.
  - Run compile/tests from `CODEX_WORKFLOW.md`.
  - Start dashboard locally and capture current screen/page behavior if requested.
  - Inventory current `outputs` keys from `run_topdown_pipeline`.
  - Confirm which fields exist in `stock_ranking`, `momentum_summary`, and backtest outputs.
  - Confirm whether root `index.html`, `app.js`, and `styles.css` are active or legacy.
- Verification:
  - Document current pages and output tables.
  - Confirm CSV and HTML export behavior.
  - Confirm no source changes unless explicitly part of the phase.
- Stop condition:
  - Stop if branch is dirty before work, tests fail, dashboard cannot start, or output fields are unclear.

### Phase 1: Design System Foundation

- Goal: add reusable UI presentation primitives without changing calculations.
- Must do:
  - Define status badges, metric rows, empty states, warning blocks, and card layout helpers.
  - Keep helpers in dashboard/UI-only modules.
  - Keep all existing pages and pipeline calls intact.
  - Add tests for pure formatting/helper behavior where practical.
- Verification:
  - Compile passes.
  - Relevant dashboard helper tests pass.
  - Manual dashboard check confirms no existing page is removed.
  - Mobile/narrow viewport check confirms cards do not overflow.
- Stop condition:
  - Stop if any existing data source, pipeline, backtest, or export behavior changes unexpectedly.

### Phase 2: Today Decision Hub

- Goal: add a first-screen decision overview from existing outputs.
- Must do:
  - Add Market Regime, Top Signals, Risk Alerts, Strategy Health, Data Freshness, and Quick Actions sections.
  - Use existing pipeline outputs only.
  - Keep missing data and demo/sample warnings visible.
  - Keep no-advice language visible.
- Verification:
  - Dashboard loads with sample/demo data.
  - Dashboard loads in Config/Yahoo mode when available.
  - Empty states render when outputs are missing.
  - Existing tests pass.
- Stop condition:
  - Stop if the hub requires new calculations or changes output semantics.

### Phase 3: Signal Cards and Filters

- Goal: present research candidates as scan-friendly signal cards with filters.
- Must do:
  - Build card view for `stock_ranking` and related available fields.
  - Add filters for sector, country, confidence/data quality, and badge where available.
  - Preserve raw table access.
  - Show unavailable fields as "Not available" or "Needs data source".
- Verification:
  - Cards render on mobile without horizontal scrolling.
  - Filtering does not mutate source data.
  - Raw `stock_ranking` table remains available.
- Stop condition:
  - Stop if card labels require invented metrics or unapproved scoring logic.

### Phase 4: Signal Detail View

- Goal: provide a single-signal explanation surface.
- Must do:
  - Add detail drawer/page state.
  - Show decision summary, signal breakdown, data quality, and supporting raw rows.
  - Add chart area only from existing price/indicator data.
  - Keep unavailable sections explicit.
- Verification:
  - Detail view works for a normal stock.
  - Detail view works for a DR/DRx signal without mixing it into Thailand domestic breadth.
  - Detail view works when metadata is missing.
- Stop condition:
  - Stop if new calculations are needed for detail sections.

### Phase 5: Backtest Evidence UX

- Goal: make opt-in backtest outputs easier to interpret.
- Must do:
  - Use existing backtest summary, portfolio, positions, instrument metrics, and warnings.
  - Explain `hit_rate`, `max_drawdown`, `observations`, and exposure fields.
  - Add sample-size and coverage warnings using existing warning outputs.
  - Keep research-assumption and no-advice labels.
- Verification:
  - Existing backtest tests pass.
  - Dashboard backtest view shows empty state when disabled.
  - Dashboard backtest view shows warnings when coverage is limited.
- Stop condition:
  - Stop if requested UI requires changing backtest calculations.

### Phase 6: Narrative Report Export UX

- Goal: improve report review/composition UX around existing export behavior.
- Must do:
  - Show report sections before export.
  - Confirm supported formats from implementation: CSV and HTML.
  - Treat Markdown/PDF as future enhancements unless implemented in a separate approved phase.
  - Preserve existing export functions.
- Verification:
  - `tests/test_report_generator.py` passes.
  - `tests/test_backtest_dashboard_report.py` passes.
  - CSV and HTML exports still produce files.
- Stop condition:
  - Stop if export implementation behavior would need to change.

### Phase 7: Polish, Accessibility, and Performance

- Goal: refine readability, responsiveness, and rendering efficiency.
- Must do:
  - Verify mobile layout.
  - Reduce excessive raw table exposure.
  - Add accessible labels and non-color status indicators.
  - Check heavy chart/table rendering behavior.
  - Keep existing behavior and calculations stable.
- Verification:
  - Full tests pass.
  - Manual dashboard check passes on desktop and mobile/narrow viewport.
  - No new dependency is added unless explicitly approved.
- Stop condition:
  - Stop if performance fixes require architectural or calculation changes.

## 14. Phase Gate Checklist

Use this checklist before completing any implementation phase:

- What changed?
- Which files changed?
- Did we preserve existing behavior?
- Did tests pass?
- Did build/compile pass?
- Did manual dashboard check pass?
- Did mobile check pass?
- Any data-quality warnings?
- Any known risks?
- Is git status clean after commit?

## 15. Suggested Commit Strategy

Use small commits that can be reviewed independently:

- `docs: add momentum dashboard redesign plan`
- `ui: add dashboard design primitives`
- `ui: add decision hub overview`
- `ui: add signal cards and filters`
- `ui: add signal detail view`
- `ui: improve backtest evidence display`
- `export: improve narrative report layout`
- `ui: polish loading empty error states`

## 16. Do Not Touch / Safety Boundaries

- Do not touch `.env`, secrets, tokens, credentials, cookies, or private keys.
- Do not change database schema unless explicitly requested.
- Do not change financial, strategy, signal, or backtest calculations unless explicitly requested.
- Do not remove existing export formats.
- Do not delete user data.
- Do not run destructive git commands.
- Do not force push.
- Do not install new dependencies without explaining why and getting approval.
- Do not add realtime data, broker integration, scraping, API keys, or live trading features.
- Do not present fake/demo data as production-ready.
- Do not hide data-quality or production-readiness warnings.

## 17. Open Questions

- What frontend stack is used?
  - Current inspected active dashboard path is Streamlit through `app.py` and `src/dashboard.py`; root `index.html`, `app.js`, and `styles.css` need inspection before assuming they are active.
- Where is the current dashboard rendered?
  - Confirmed: Streamlit in `src/dashboard.py`.
- What data powers momentum score?
  - Likely `src/momentum.py` and `momentum_summary`, plus `stock_ranking` research score. Exact output fields should be confirmed in Phase 0.
- What export formats already exist?
  - Confirmed: CSV and HTML. Markdown/PDF are not confirmed.
- Is there a watchlist feature?
  - Unknown / needs inspection.
- Are sector/industry fields available?
  - Available when metadata/reference data includes them; missing metadata must be handled as unavailable.
- Are backtest summary metrics already available?
  - Confirmed: `total_return`, `annualized_volatility`, `max_drawdown`, `hit_rate`, `turnover`, `average_gross_exposure`, `observations`, and `signal_type`.
- What commands should be used for test/build/lint?
  - Confirmed workflow commands: `.\.venv\Scripts\python.exe -m compileall src` and `.\.venv\Scripts\python.exe -m pytest --basetemp=tmp_pytest`.
  - No separate lint command was identified.

