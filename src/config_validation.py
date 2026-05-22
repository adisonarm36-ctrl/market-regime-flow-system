from __future__ import annotations

import pandas as pd


KNOWN_SECURITY_TYPES = {"Stock", "DR", "DRx", "DW", "ETF", "warrant", "Warrant"}
REQUIRED_METADATA_COLUMNS = [
    "Ticker",
    "SecurityType",
    "Country",
    "Sector",
    "Industry",
    "Universe",
    "Suspended",
    "average_traded_value_20d",
]


def validate_metadata_schema(metadata_df: pd.DataFrame) -> list[str]:
    """Validate metadata columns and known security types."""
    warnings: list[str] = []
    missing = [column for column in REQUIRED_METADATA_COLUMNS if column not in metadata_df.columns]
    if missing:
        warnings.append(f"Missing metadata columns: {', '.join(missing)}")
        return warnings

    unknown_types = sorted(set(metadata_df["SecurityType"].dropna()) - KNOWN_SECURITY_TYPES)
    if unknown_types:
        warnings.append(f"Unknown security type values: {', '.join(unknown_types)}")
    return warnings


def validate_country_universe(country_config: dict) -> list[str]:
    """Warn when country universe config is missing or has no populated country lists."""
    countries = country_config.get("countries")
    if not isinstance(countries, dict) or not countries:
        return ["Missing country universe config: countries"]
    if not any(bool(tickers) for tickers in countries.values()):
        return ["Country universe config has no populated ticker lists"]
    return []


def validate_sector_mapping(sector_config: dict) -> list[str]:
    """Warn when sector and industry mappings are missing or empty."""
    if not sector_config.get("sectors") and not sector_config.get("industries"):
        return ["Missing sector mapping: sectors and industries are empty"]
    return []


def validate_dr_underlyings(dr_mapping_df: pd.DataFrame, available_tickers: set[str] | None = None) -> list[str]:
    """Validate DR mappings and optionally check underlying availability."""
    warnings: list[str] = []
    if dr_mapping_df.empty:
        return ["Missing DR mappings"]
    required = {"DR_Ticker", "Underlying_Ticker"}
    missing = required.difference(dr_mapping_df.columns)
    if missing:
        return [f"Missing DR mapping columns: {', '.join(sorted(missing))}"]
    missing_underlying = dr_mapping_df["Underlying_Ticker"].isna() | dr_mapping_df["Underlying_Ticker"].eq("")
    if missing_underlying.any():
        warnings.append(f"Missing DR underlying values: {int(missing_underlying.sum())}")
    if available_tickers is not None:
        unavailable = sorted(set(dr_mapping_df["Underlying_Ticker"].dropna()) - available_tickers)
        if unavailable:
            warnings.append(f"DR underlying not found in prices: {', '.join(unavailable)}")
    return warnings


def validate_thresholds(threshold_config: dict, section: str, required_keys: list[str]) -> list[str]:
    """Validate required threshold keys for a config section."""
    values = threshold_config.get(section)
    if not isinstance(values, dict):
        return [f"Missing thresholds section: {section}"]
    missing = [key for key in required_keys if key not in values]
    return [f"Missing threshold keys for {section}: {', '.join(missing)}"] if missing else []
