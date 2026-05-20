from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd


REQUIRED_OHLCV_COLUMNS = ["Date", "Ticker", "Open", "High", "Low", "Close", "Volume"]


@dataclass(frozen=True)
class ValidationResult:
    """Structured data validation output."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_required_columns(df: pd.DataFrame, required_columns: Iterable[str] = REQUIRED_OHLCV_COLUMNS) -> list[str]:
    """Return missing required OHLCV columns."""
    return [column for column in required_columns if column not in df.columns]


def find_missing_data(df: pd.DataFrame, columns: Iterable[str] | None = None) -> pd.DataFrame:
    """Return rows that contain missing values in selected columns."""
    check_columns = list(columns) if columns is not None else list(df.columns)
    return df[df[check_columns].isna().any(axis=1)]


def find_duplicate_rows(df: pd.DataFrame, subset: Iterable[str] = ("Date", "Ticker")) -> pd.DataFrame:
    """Return duplicate rows for a Date/Ticker key."""
    subset_list = list(subset)
    return df[df.duplicated(subset=subset_list, keep=False)].sort_values(subset_list)


def validate_ohlcv(df: pd.DataFrame) -> ValidationResult:
    """Validate an OHLCV table without mutating input data."""
    errors: list[str] = []
    warnings: list[str] = []

    missing_columns = validate_required_columns(df)
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        return ValidationResult(False, errors, warnings)

    missing_rows = find_missing_data(df, REQUIRED_OHLCV_COLUMNS)
    if not missing_rows.empty:
        errors.append(f"Missing data found in {len(missing_rows)} rows")

    duplicate_rows = find_duplicate_rows(df)
    if not duplicate_rows.empty:
        errors.append(f"Duplicate Date/Ticker rows found: {len(duplicate_rows)} rows")

    if "Adjusted Close" not in df.columns and "Adj Close" not in df.columns:
        warnings.append("Adjusted Close is not available; Close will be used")

    return ValidationResult(is_valid=not errors, errors=errors, warnings=warnings)
