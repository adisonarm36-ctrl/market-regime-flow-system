# Run State

## Last Completed Work

Phase 8A.1: Yahoo candidate map generation fix.

The project is safe to continue from the current codebase. CSV remains supported, manual upload remains an Advanced/Fallback workflow, Yahoo/yfinance is historical/cache-based only, and opt-in backtests are research assumptions only.

Config source mode now has an explicit `Use bundled fake/demo reference files` toggle. When enabled, missing local reference paths are mapped at runtime to bundled fake/sample files without editing `config/data_sources.yaml`. Production missing-reference warnings remain visible, and demo reference data is labeled as not suitable for production research.

Before configured Yahoo loading runs, the dashboard now shows a startup checklist covering active source, yfinance availability, configured tickers, cache directory/file status when available, local reference coverage, missing references, demo mode state, manual upload fallback availability, and actionable blockers.

The dashboard now includes an explicit `Run Yahoo historical smoke test` button that uses configured tickers and cache-first behavior, then reports rows loaded, date range, cache status, warnings, and errors. It is labeled as a historical connectivity/cache check only.

The dashboard now reports production reference readiness for configured local files. It checks required columns, fake/sample file usage, missing files, and local Yahoo ticker fields without inventing mappings or classifications.

The repo now includes `scripts/bootstrap_yahoo_reference_data.py` and `src/yahoo_reference_bootstrap.py` to generate Yahoo-derived metadata, sector, country, asset-map, and download-report candidates under `data/reference/generated/`. Generated CSVs are local ignored artifacts and every row is marked `NeedsReview`; they do not replace production reference files.

Yahoo sector/country candidate generation now emits reviewable map rows when Yahoo metadata or conservative fallback fields exist. Sector/country map candidates include `YahooTicker`, `IsFallbackDerived`, missing-field notes, and provenance notes. Default sample asset-map hints can produce review-only sector candidates, while country fallback remains limited to obvious crypto `-USD` pairs unless Yahoo supplies country metadata.

The repo now also includes `scripts/promote_yahoo_candidates.py` and `src/yahoo_candidate_promotion.py`. Promotion is dry-run by default, only accepts `Reviewed` or `Approved` rows, reports configured ticker coverage gaps, backs up existing production CSVs before overwrite, and requires `--apply` to write production files.

First-run usability is complete through Phase 7F. README, status, run-state, phase plan, and first-run plan docs now describe the dependency diagnostics, demo reference mode, startup checklist, Yahoo historical smoke test, production reference readiness, manual upload fallback, common first-run errors, and known pytest cache warning.

## Current Test Result

`173 passed` on 2026-05-30 with Python 3.11.9.

The warning is the known Windows `.pytest_cache` creation/cleanup issue documented in `TROUBLESHOOTING.md`; it does not affect tracked files or test pass/fail status.

## Next Phase

After Phase 8A.1 verification, recommended next work remains manual review of generated Yahoo candidate rows before any promotion.

Recommended next work is user-provided DR/DRx mapping and Thailand-specific DR quality data verification, plus manual review of generated Yahoo candidate rows before any promotion.

## Exact Next Prompt

```text
Read AGENTS.md, CODEX_WORKFLOW.md, RUN_STATE.md, PROJECT_STATUS.md, PHASE_PLAN.md, and TROUBLESHOOTING.md first.

Review generated Yahoo candidate CSVs and promote only manually verified rows.

Goal:
Manually verify Yahoo-derived and fallback-derived candidate rows before production promotion.

Tasks:
- Run `scripts/bootstrap_yahoo_reference_data.py`.
- Review generated metadata, sector, country, and asset-map candidates.
- Change only trusted rows from `NeedsReview` to `Reviewed` or `Approved`.
- Run `scripts/promote_yahoo_candidates.py` dry-run before any `--apply`.
```

## Handoff Notes

- Read `AGENTS.md` before continuing.
- Read `CODEX_WORKFLOW.md`, `PROJECT_STATUS.md`, `PHASE_PLAN.md`, and `TROUBLESHOOTING.md` before coding.
- Do not add live APIs unless a later explicit phase requires and configures them.
- Do not present fake/demo data as real market data.
- Preserve CSV and manual upload fallback.
- Preserve Yahoo as historical price-only source.
- Keep DR/DRx separate from Thailand domestic breadth.
- Bundled Thailand reference files are fake/demo samples only.
- Demo reference bootstrap mode is fake/sample data for smoke testing only.
- Startup checklist helpers must remain network-free.
- Yahoo smoke test is historical/cache-only and not data completeness validation.
- Production readiness checks must never infer missing mappings or classifications.
- Yahoo historical data is price-only; local reference files remain required for metadata, Thailand universe, DR/DRx mapping, security type, sector/country maps, and local DR quality data.
- Yahoo metadata bootstrap outputs are candidates only and must remain under generated ignored files until manually reviewed.
- Yahoo candidate promotion is user-run only; do not promote `NeedsReview` rows and do not commit real generated or production CSV outputs created locally.
- Do not invent Yahoo ticker mappings.
