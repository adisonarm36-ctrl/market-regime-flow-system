from __future__ import annotations

from pathlib import Path

import pandas as pd


THAILAND_UNIVERSE_COLUMNS = [
    "Ticker",
    "Name",
    "Country",
    "Exchange",
    "Universe",
    "SecurityType",
    "Sector",
    "Industry",
    "Currency",
    "IsDR",
    "IsDRx",
    "IsETF",
    "IsDW",
    "IsWarrant",
    "Suspended",
    "IncludeInDomesticBreadth",
    "Notes",
]
THAILAND_SECTOR_MAP_COLUMNS = ["Ticker", "Sector", "Industry", "Country", "Exchange", "Universe"]
THAILAND_SECURITY_TYPES_COLUMNS = [
    "Ticker",
    "SecurityType",
    "IsDomesticStock",
    "IsDR",
    "IsDRx",
    "IsETF",
    "IsDW",
    "IsWarrant",
    "Suspended",
    "IncludeInDomesticBreadth",
    "ExclusionReason",
]
THAILAND_LIQUIDITY_COLUMNS = [
    "Ticker",
    "average_traded_value_20d",
    "average_volume_20d",
    "trading_days_ratio_60d",
    "liquidity_bucket",
    "Notes",
]
THAILAND_DR_MAPPING_COLUMNS = [
    "DR_Ticker",
    "DR_Type",
    "UnderlyingTicker",
    "UnderlyingName",
    "UnderlyingExchange",
    "UnderlyingCountry",
    "UnderlyingCurrency",
    "DR_Currency",
    "Ratio",
    "IssuerCode",
    "LocalExchange",
    "IsActive",
    "HasFairValueInput",
    "FairValueSource",
    "FXPair",
    "Notes",
]

BOOLEAN_COLUMNS = {
    "IsDR",
    "IsDRx",
    "IsETF",
    "IsDW",
    "IsWarrant",
    "Suspended",
    "IncludeInDomesticBreadth",
    "IsDomesticStock",
    "IsActive",
    "HasFairValueInput",
}
ALLOWED_SECURITY_TYPES = {"Common Stock", "Stock", "Domestic Stock", "DR", "DRx", "ETF", "DW", "Warrant"}
ALLOWED_UNIVERSES = {"SET50", "SET100", "SET", "mai", "SET ex-DR", "Custom"}


def load_thailand_universe(path: str | Path) -> pd.DataFrame:
    """Load Thailand local universe reference data and normalize boolean flags."""
    df = pd.read_csv(_require_path(path))
    warnings = validate_thailand_universe_schema(df)
    result = _normalize_boolean_columns(df)
    result.attrs["warnings"] = warnings
    return result


def load_thailand_sector_map(path: str | Path) -> pd.DataFrame:
    """Load Thailand sector and industry map reference data."""
    df = pd.read_csv(_require_path(path))
    warnings = validate_thailand_sector_map_schema(df)
    df.attrs["warnings"] = warnings
    return df


def load_thailand_security_types(path: str | Path) -> pd.DataFrame:
    """Load Thailand security type flags used for domestic breadth eligibility."""
    df = pd.read_csv(_require_path(path))
    warnings = validate_thailand_security_types_schema(df)
    result = _normalize_boolean_columns(df)
    result.attrs["warnings"] = warnings
    return result


def load_thailand_liquidity(path: str | Path) -> pd.DataFrame:
    """Load local Thailand liquidity reference metrics."""
    df = pd.read_csv(_require_path(path))
    warnings = validate_thailand_liquidity_schema(df)
    result = df.copy()
    for column in ["average_traded_value_20d", "average_volume_20d", "trading_days_ratio_60d"]:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    result.attrs["warnings"] = warnings
    return result


def load_thailand_dr_mapping(path: str | Path) -> pd.DataFrame:
    """Load local Thailand DR/DRx mapping reference data."""
    df = pd.read_csv(_require_path(path))
    warnings = validate_thailand_dr_mapping_schema(df)
    result = _normalize_boolean_columns(df)
    if "Ratio" in result.columns:
        result["Ratio"] = pd.to_numeric(result["Ratio"], errors="coerce")
    result.attrs["warnings"] = warnings
    return result


def validate_thailand_universe_schema(df: pd.DataFrame) -> list[str]:
    """Validate Thailand universe schema and return non-fatal warnings."""
    _require_columns(df, THAILAND_UNIVERSE_COLUMNS, "Thailand universe")
    warnings = _reference_warnings(df)
    return warnings


def validate_thailand_sector_map_schema(df: pd.DataFrame) -> list[str]:
    """Validate Thailand sector map schema."""
    _require_columns(df, THAILAND_SECTOR_MAP_COLUMNS, "Thailand sector map")
    warnings = []
    unknown_universe = _unknown_values(df, "Universe", ALLOWED_UNIVERSES)
    if unknown_universe:
        warnings.append(f"Unknown Universe values: {', '.join(unknown_universe)}")
    return warnings


def validate_thailand_security_types_schema(df: pd.DataFrame) -> list[str]:
    """Validate Thailand security type schema and flag unknown types."""
    _require_columns(df, THAILAND_SECURITY_TYPES_COLUMNS, "Thailand security types")
    return _reference_warnings(df)


def validate_thailand_liquidity_schema(df: pd.DataFrame) -> list[str]:
    """Validate Thailand liquidity schema."""
    _require_columns(df, THAILAND_LIQUIDITY_COLUMNS, "Thailand liquidity")
    warnings = []
    for column in ["average_traded_value_20d", "average_volume_20d", "trading_days_ratio_60d"]:
        invalid = pd.to_numeric(df[column], errors="coerce").isna() & df[column].notna()
        if invalid.any():
            warnings.append(f"{column} has non-numeric values in {int(invalid.sum())} rows")
    return warnings


def validate_thailand_dr_mapping_schema(df: pd.DataFrame) -> list[str]:
    """Validate Thailand DR/DRx mapping schema."""
    _require_columns(df, THAILAND_DR_MAPPING_COLUMNS, "Thailand DR mapping")
    if df["UnderlyingTicker"].isna().any() or df["UnderlyingTicker"].astype(str).str.strip().eq("").any():
        raise ValueError("Thailand DR mapping has missing UnderlyingTicker values")
    warnings = []
    unknown_type = sorted(set(df["DR_Type"].dropna().astype(str)) - {"DR", "DRx"})
    if unknown_type:
        warnings.append(f"Unknown DR_Type values: {', '.join(unknown_type)}")
    for optional in ["HasFairValueInput", "FairValueSource", "FXPair"]:
        if optional not in df.columns:
            warnings.append(f"Optional DR fair value field missing: {optional}")
    invalid_ratio = pd.to_numeric(df["Ratio"], errors="coerce").isna() & df["Ratio"].notna()
    if invalid_ratio.any():
        warnings.append(f"Ratio has non-numeric values in {int(invalid_ratio.sum())} rows")
    return warnings


def normalize_boolean_series(series: pd.Series) -> pd.Series:
    """Normalize common local-reference boolean values without inventing missing data."""
    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
        "y": True,
        "n": False,
    }

    def convert(value):
        if pd.isna(value):
            return pd.NA
        if isinstance(value, bool):
            return value
        key = str(value).strip().lower()
        if key not in mapping:
            raise ValueError(f"Invalid boolean-like value: {value}")
        return mapping[key]

    return series.map(convert).astype("boolean")


def _normalize_boolean_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in sorted(BOOLEAN_COLUMNS.intersection(result.columns)):
        result[column] = normalize_boolean_series(result[column])
    return result


def _reference_warnings(df: pd.DataFrame) -> list[str]:
    warnings = []
    unknown_type = _unknown_values(df, "SecurityType", ALLOWED_SECURITY_TYPES)
    if unknown_type:
        warnings.append(f"Unknown SecurityType values: {', '.join(unknown_type)}")
    unknown_universe = _unknown_values(df, "Universe", ALLOWED_UNIVERSES)
    if unknown_universe:
        warnings.append(f"Unknown Universe values: {', '.join(unknown_universe)}")
    return warnings


def _unknown_values(df: pd.DataFrame, column: str, allowed: set[str]) -> list[str]:
    if column not in df.columns:
        return []
    values = set(df[column].dropna().astype(str).str.strip())
    return sorted(value for value in values if value and value not in allowed)


def _require_columns(df: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required {label} columns: {', '.join(missing)}")


def _require_path(path: str | Path) -> Path:
    ref_path = Path(path)
    if not str(path):
        raise FileNotFoundError("Thailand reference path is blank")
    if not ref_path.exists():
        raise FileNotFoundError(f"Thailand reference path not found: {ref_path}")
    return ref_path
