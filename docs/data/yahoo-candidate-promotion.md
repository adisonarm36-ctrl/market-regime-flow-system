# Yahoo Candidate Promotion

Phase 8B adds a guarded workflow for copying manually reviewed Yahoo-derived candidate CSV rows into production reference CSVs.

Promotion is never automatic. The dashboard does not run this workflow. The script defaults to dry-run mode and writes production files only when `--apply` is supplied.

## Before Promotion

1. Generate candidate files with `scripts/bootstrap_yahoo_reference_data.py`.
2. Open the generated CSVs under `data/reference/generated/`.
3. Verify each row manually against trusted sources.
4. Change `VerificationStatus` from `NeedsReview` to `Reviewed` or `Approved`.
5. Fill required production fields such as `Universe` and `Suspended` for metadata rows.
6. Keep `Source = Yahoo` and `IsYahooDerived = true` so provenance remains visible.
7. Review any `IsFallbackDerived = true`, `FallbackFields`, `MissingFields`, or `Notes` values carefully; fallback-derived rows are not verified production classifications.

Rows left as `NeedsReview` are not promoted.

## Dry Run

Dry-run validates candidates and reports coverage gaps without writing production files:

```powershell
.\.venv\Scripts\python.exe scripts\promote_yahoo_candidates.py
```

Use custom paths when reviewing a copied candidate directory:

```powershell
.\.venv\Scripts\python.exe scripts\promote_yahoo_candidates.py --candidate-dir data/reference/generated --output-dir data/reference
```

## Apply Promotion

Only apply after dry-run validation is clean and coverage gaps are understood:

```powershell
.\.venv\Scripts\python.exe scripts\promote_yahoo_candidates.py --apply
```

The script writes:

- `data/reference/metadata.csv`
- `data/reference/sector_map.csv`
- `data/reference/country_map.csv`
- `data/reference/asset_map.csv`

If any existing production file is present, it is copied to `data/reference/backups/` before overwrite.

## Rollback

To roll back, copy the desired backup file from `data/reference/backups/` back to its production path. Example:

```powershell
Copy-Item data/reference/backups/metadata.<timestamp>.csv data/reference/metadata.csv
```

Review the backup timestamp carefully before copying.

## Validation Rules

The promotion workflow checks:

- required columns exist
- rows are `Reviewed` or `Approved`
- `Source` remains `Yahoo`
- `IsYahooDerived` remains true
- fallback provenance columns remain visible where generated
- important fields are not blank
- duplicate reviewed tickers are blocked
- configured Yahoo ticker coverage gaps are reported

Blank important fields can be allowed only through an explicit command flag such as:

```powershell
.\.venv\Scripts\python.exe scripts\promote_yahoo_candidates.py --allow-blank-field Universe
```

Use that sparingly and only after documenting why a field is intentionally blank.

## What Still Requires User Data

Yahoo candidate promotion does not create or infer:

- DR/DRx mappings
- Thailand domestic security eligibility
- Thailand-specific DR quality data
- bid/ask, liquidity, fair-value, FX, or underlying-price files
- realtime data, broker data, API-key data, or trading instructions

Those inputs remain user-provided and manually verified in later workflow phases.
