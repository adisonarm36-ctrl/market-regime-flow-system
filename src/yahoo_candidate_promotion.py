from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.yahoo_reference_bootstrap import (
    ASSET_MAP_COLUMNS,
    COUNTRY_MAP_COLUMNS,
    METADATA_COLUMNS,
    SECTOR_MAP_COLUMNS,
    configured_yahoo_tickers,
)


ACCEPTED_REVIEW_STATUSES = {"Reviewed", "Approved"}
AUDIT_COLUMNS = ["Source", "VerificationStatus", "IsYahooDerived"]
CANDIDATE_FILES = {
    "metadata": "yahoo_metadata_candidates.csv",
    "sector_map": "yahoo_sector_map_candidates.csv",
    "country_map": "yahoo_country_map_candidates.csv",
    "asset_map": "yahoo_asset_map_candidates.csv",
}
PRODUCTION_FILES = {
    "metadata": "metadata.csv",
    "sector_map": "sector_map.csv",
    "country_map": "country_map.csv",
    "asset_map": "asset_map.csv",
}
BASE_REQUIRED_COLUMNS = {
    "metadata": [*METADATA_COLUMNS, "Universe", "Suspended"],
    "sector_map": SECTOR_MAP_COLUMNS,
    "country_map": COUNTRY_MAP_COLUMNS,
    "asset_map": ASSET_MAP_COLUMNS,
}
IMPORTANT_FIELDS = {
    "metadata": ["Ticker", "SecurityType", "Country", "Sector", "Industry", "Universe", "Suspended", *AUDIT_COLUMNS],
    "sector_map": ["Ticker", "Sector", "Industry", *AUDIT_COLUMNS],
    "country_map": ["Ticker", "Country", *AUDIT_COLUMNS],
    "asset_map": ["Ticker", "asset_class", "group", "subgroup", *AUDIT_COLUMNS],
}


@dataclass(frozen=True)
class PromotionPlan:
    """Validated promotion result for reviewed Yahoo candidate files."""

    outputs: dict[str, pd.DataFrame]
    validation_report: pd.DataFrame
    coverage_report: pd.DataFrame
    backups: dict[str, Path]
    written_paths: dict[str, Path]
    apply: bool

    @property
    def has_errors(self) -> bool:
        return bool(self.validation_report["severity"].eq("error").any()) if not self.validation_report.empty else False


def promote_reviewed_yahoo_candidates(
    candidate_dir: str | Path = "data/reference/generated",
    output_dir: str | Path = "data/reference",
    config_path: str | Path = "config/data_sources.yaml",
    apply: bool = False,
    accepted_statuses: Iterable[str] = ACCEPTED_REVIEW_STATUSES,
    allow_blank_fields: Iterable[str] | None = None,
    backup_dir: str | Path | None = None,
) -> PromotionPlan:
    """Validate and optionally promote reviewed Yahoo candidates into production CSVs."""
    accepted = {str(status).strip() for status in accepted_statuses if str(status).strip()}
    allowed_blanks = {str(field).strip() for field in (allow_blank_fields or []) if str(field).strip()}
    candidates = load_candidate_tables(candidate_dir)
    outputs: dict[str, pd.DataFrame] = {}
    validation_rows: list[dict[str, object]] = []
    for name, table in candidates.items():
        table_errors = validate_candidate_table(name, table, accepted, allowed_blanks)
        validation_rows.extend(table_errors)
        outputs[name] = filter_promotable_rows(table, accepted) if not table.empty else pd.DataFrame(columns=table.columns)

    coverage_report = build_ticker_coverage_report(outputs, configured_yahoo_tickers(config_path))
    validation_report = pd.DataFrame(validation_rows, columns=["file", "severity", "check", "detail"])
    if apply and not validation_report.empty and validation_report["severity"].eq("error").any():
        raise ValueError("Promotion blocked by validation errors. Run dry-run and fix candidate files first.")

    backups: dict[str, Path] = {}
    written_paths: dict[str, Path] = {}
    if apply:
        backups = backup_existing_outputs(output_dir, backup_dir=backup_dir)
        written_paths = write_promoted_outputs(outputs, output_dir)
    return PromotionPlan(
        outputs=outputs,
        validation_report=validation_report,
        coverage_report=coverage_report,
        backups=backups,
        written_paths=written_paths,
        apply=apply,
    )


def load_candidate_tables(candidate_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Load all generated Yahoo candidate CSVs from the local generated directory."""
    root = Path(candidate_dir)
    return {
        name: _read_csv_or_empty(root / file_name, BASE_REQUIRED_COLUMNS[name])
        for name, file_name in CANDIDATE_FILES.items()
    }


def validate_candidate_table(
    name: str,
    table: pd.DataFrame,
    accepted_statuses: set[str],
    allow_blank_fields: set[str] | None = None,
) -> list[dict[str, object]]:
    """Return validation rows for one candidate table without mutating it."""
    allowed_blanks = allow_blank_fields or set()
    rows: list[dict[str, object]] = []
    required_columns = BASE_REQUIRED_COLUMNS[name]
    missing_columns = [column for column in required_columns if column not in table.columns]
    if missing_columns:
        rows.append(_validation_row(name, "error", "required_columns", f"Missing columns: {', '.join(missing_columns)}"))
        return rows
    if table.empty:
        rows.append(_validation_row(name, "warning", "empty_file", "Candidate file has no rows to promote."))
        return rows

    reviewed = filter_promotable_rows(table, accepted_statuses)
    if reviewed.empty:
        rows.append(_validation_row(name, "error", "review_status", f"No rows have VerificationStatus in: {', '.join(sorted(accepted_statuses))}"))

    needs_review = table[~table["VerificationStatus"].astype(str).str.strip().isin(accepted_statuses)]
    if not needs_review.empty:
        rows.append(_validation_row(name, "warning", "unpromoted_rows", f"{len(needs_review)} row(s) remain unpromoted because they are not Reviewed/Approved."))

    for column, expected in [("Source", "Yahoo"), ("IsYahooDerived", True)]:
        invalid = reviewed[~reviewed[column].map(lambda value: _matches_expected(value, expected))]
        if not invalid.empty:
            tickers = ", ".join(invalid["Ticker"].astype(str).tolist())
            rows.append(_validation_row(name, "error", column, f"{column} is not {expected!r} for: {tickers}"))

    for column in IMPORTANT_FIELDS[name]:
        if column in allowed_blanks:
            continue
        blank = reviewed[reviewed[column].map(_is_blank)]
        if not blank.empty:
            tickers = ", ".join(blank["Ticker"].astype(str).tolist())
            rows.append(_validation_row(name, "error", "blank_field", f"{column} is blank for: {tickers}"))

    duplicate_tickers = reviewed.loc[reviewed["Ticker"].duplicated(keep=False), "Ticker"].astype(str).tolist()
    if duplicate_tickers:
        rows.append(_validation_row(name, "error", "duplicate_tickers", f"Duplicate reviewed tickers: {', '.join(sorted(set(duplicate_tickers)))}"))
    return rows


def filter_promotable_rows(table: pd.DataFrame, accepted_statuses: set[str]) -> pd.DataFrame:
    """Return rows explicitly marked Reviewed or Approved."""
    if table.empty or "VerificationStatus" not in table.columns:
        return pd.DataFrame(columns=table.columns)
    mask = table["VerificationStatus"].astype(str).str.strip().isin(accepted_statuses)
    return table.loc[mask].copy()


def build_ticker_coverage_report(outputs: dict[str, pd.DataFrame], configured_tickers: list[str]) -> pd.DataFrame:
    """Report configured Yahoo ticker coverage in each promoted output table."""
    configured = set(configured_tickers)
    rows = []
    for name, table in outputs.items():
        present = set(table["Ticker"].dropna().astype(str)) if "Ticker" in table.columns else set()
        missing = sorted(configured - present)
        extra = sorted(present - configured)
        rows.append(
            {
                "file": name,
                "configured_tickers": len(configured),
                "promoted_tickers": len(present),
                "missing_configured_tickers": ", ".join(missing),
                "extra_promoted_tickers": ", ".join(extra),
                "status": "ok" if not missing else "gap",
            }
        )
    return pd.DataFrame(rows)


def backup_existing_outputs(
    output_dir: str | Path = "data/reference",
    backup_dir: str | Path | None = None,
    timestamp: str | None = None,
) -> dict[str, Path]:
    """Back up existing production CSV files before promotion overwrites them."""
    root = Path(output_dir)
    backup_root = Path(backup_dir) if backup_dir else root / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or datetime.now().strftime("%Y%m%d%H%M%S")
    backups: dict[str, Path] = {}
    for name, file_name in PRODUCTION_FILES.items():
        source = root / file_name
        if not source.exists():
            continue
        target = backup_root / f"{source.stem}.{stamp}{source.suffix}"
        shutil.copy2(source, target)
        backups[name] = target
    return backups


def write_promoted_outputs(outputs: dict[str, pd.DataFrame], output_dir: str | Path = "data/reference") -> dict[str, Path]:
    """Write reviewed candidate rows into production CSV paths."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, table in outputs.items():
        path = root / PRODUCTION_FILES[name]
        table.to_csv(path, index=False)
        written[name] = path
    return written


def _read_csv_or_empty(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    return pd.read_csv(path)


def _validation_row(file_name: str, severity: str, check: str, detail: str) -> dict[str, object]:
    return {"file": file_name, "severity": severity, "check": check, "detail": detail}


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def _matches_expected(value: object, expected: object) -> bool:
    if isinstance(expected, bool):
        if isinstance(value, bool):
            return value is expected
        return str(value).strip().lower() == str(expected).lower()
    return str(value).strip() == str(expected)
