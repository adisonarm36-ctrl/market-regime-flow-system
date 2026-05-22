from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config_loader import load_yaml
from .reference_data import _load_tabular_reference
from .thailand_reference import normalize_boolean_series


REQUIRED_DR_MAPPING_COLUMNS = ["DR_Ticker", "Underlying_Ticker"]
THAILAND_REQUIRED_DR_MAPPING_COLUMNS = [
    "DR_Ticker",
    "DR_Type",
    "UnderlyingTicker",
    "UnderlyingExchange",
    "UnderlyingCountry",
    "UnderlyingCurrency",
    "DR_Currency",
    "Ratio",
    "IssuerCode",
    "IsActive",
]


def load_dr_mapping(path: str | Path) -> pd.DataFrame:
    """Load DR-to-underlying mapping from CSV or YAML local reference data."""
    ref_path = Path(path)
    if ref_path.suffix.lower() in {".yaml", ".yml"}:
        config = load_yaml(ref_path)
        rows = config.get("dr_mappings", [])
        df = pd.DataFrame(rows)
    else:
        df = _load_tabular_reference(ref_path)
    return normalize_dr_mapping(df)


def validate_dr_mapping_schema(df: pd.DataFrame) -> list[str]:
    """Validate Thailand-style DR/DRx mapping schema and return non-fatal warnings."""
    normalized = normalize_dr_mapping(df)
    missing = [column for column in THAILAND_REQUIRED_DR_MAPPING_COLUMNS if column not in normalized.columns]
    if missing:
        raise ValueError(f"Missing required DR mapping columns: {', '.join(missing)}")
    missing_underlying = normalized["UnderlyingTicker"].isna() | normalized["UnderlyingTicker"].astype(str).str.strip().eq("")
    if missing_underlying.any():
        raise ValueError("Missing underlying ticker in DR mapping")
    invalid_type = sorted(set(normalized["DR_Type"].dropna().astype(str)) - {"DR", "DRx"})
    warnings = []
    if invalid_type:
        warnings.append(f"Unknown DR_Type values: {', '.join(invalid_type)}")
    invalid_ratio = pd.to_numeric(normalized["Ratio"], errors="coerce").isna() & normalized["Ratio"].notna()
    if invalid_ratio.any():
        warnings.append(f"Ratio has non-numeric values in {int(invalid_ratio.sum())} rows")
    for optional in ["HasFairValueInput", "FairValueSource", "FXPair"]:
        if optional not in normalized.columns:
            warnings.append(f"Optional DR fair value field missing: {optional}")
    return warnings


def normalize_dr_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DR mapping column aliases and boolean/numeric fields."""
    result = df.copy()
    if "UnderlyingTicker" not in result.columns and "Underlying_Ticker" in result.columns:
        result["UnderlyingTicker"] = result["Underlying_Ticker"]
    if "Underlying_Ticker" not in result.columns and "UnderlyingTicker" in result.columns:
        result["Underlying_Ticker"] = result["UnderlyingTicker"]
    if "DR_Type" not in result.columns:
        result["DR_Type"] = "DR"
    if "IsActive" in result.columns:
        result["IsActive"] = normalize_boolean_series(result["IsActive"])
    if "HasFairValueInput" in result.columns:
        result["HasFairValueInput"] = normalize_boolean_series(result["HasFairValueInput"])
    if "Ratio" in result.columns:
        result["Ratio"] = pd.to_numeric(result["Ratio"], errors="coerce")
    return result


def group_drs_by_underlying(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Group DR/DRx rows by underlying ticker."""
    normalized = normalize_dr_mapping(df)
    if "UnderlyingTicker" not in normalized.columns:
        raise ValueError("DR mapping must include UnderlyingTicker or Underlying_Ticker")
    return {underlying: group.copy() for underlying, group in normalized.groupby("UnderlyingTicker", dropna=False)}


def get_dr_candidates_for_underlying(df: pd.DataFrame, underlying_ticker: str) -> pd.DataFrame:
    """Return DR/DRx candidates for a specific underlying ticker."""
    normalized = normalize_dr_mapping(df)
    return normalized[normalized["UnderlyingTicker"].eq(underlying_ticker)].copy().reset_index(drop=True)


def identify_duplicate_dr_underlyings(df: pd.DataFrame) -> pd.DataFrame:
    """Identify underlying instruments with more than one DR/DRx reference row."""
    normalized = normalize_dr_mapping(df)
    if "UnderlyingTicker" not in normalized.columns or normalized.empty:
        return pd.DataFrame(columns=["UnderlyingTicker", "dr_count", "DR_Tickers"])
    grouped = normalized.groupby("UnderlyingTicker")["DR_Ticker"].agg(list).reset_index()
    grouped["dr_count"] = grouped["DR_Ticker"].map(len)
    grouped = grouped[grouped["dr_count"].gt(1)].copy()
    grouped["DR_Tickers"] = grouped["DR_Ticker"].map(lambda values: ", ".join(map(str, values)))
    return grouped[["UnderlyingTicker", "dr_count", "DR_Tickers"]].reset_index(drop=True)


def validate_dr_mapping(mapping_df: pd.DataFrame) -> list[str]:
    """Validate required DR mapping fields and duplicate DR tickers."""
    mapping_df = normalize_dr_mapping(mapping_df)
    errors: list[str] = []
    missing = [column for column in REQUIRED_DR_MAPPING_COLUMNS if column not in mapping_df.columns]
    if missing:
        errors.append(f"Missing required DR mapping columns: {', '.join(missing)}")
        return errors

    missing_rows = mapping_df[REQUIRED_DR_MAPPING_COLUMNS].isna().any(axis=1)
    if missing_rows.any():
        errors.append(f"Missing DR mapping values in {int(missing_rows.sum())} rows")

    duplicate_count = int(mapping_df.duplicated(subset=["DR_Ticker"], keep=False).sum())
    if duplicate_count:
        errors.append(f"Duplicate DR_Ticker rows found: {duplicate_count}")

    return errors


def attach_underlying_signal(dr_mapping_df: pd.DataFrame, signal_df: pd.DataFrame, signal_ticker_column: str = "Ticker") -> pd.DataFrame:
    """Attach underlying signal metrics to DR rows without using DR prices for signal generation."""
    dr_mapping_df = normalize_dr_mapping(dr_mapping_df)
    errors = validate_dr_mapping(dr_mapping_df)
    if errors:
        raise ValueError("; ".join(errors))
    if signal_ticker_column not in signal_df.columns:
        raise ValueError(f"signal_df must include {signal_ticker_column}")

    signal = signal_df.rename(columns={signal_ticker_column: "Underlying_Ticker"})
    merged = dr_mapping_df.merge(signal, on="Underlying_Ticker", how="left", indicator=True)
    merged["signal_status"] = merged["_merge"].map({"both": "available", "left_only": "missing_underlying_signal", "right_only": "unexpected"})
    return merged.drop(columns=["_merge"])
