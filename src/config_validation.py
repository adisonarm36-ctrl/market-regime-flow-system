from __future__ import annotations

from pathlib import Path
from copy import deepcopy

import pandas as pd


KNOWN_SECURITY_TYPES = {"Stock", "DR", "DRx", "DW", "ETF", "warrant", "Warrant"}
SUPPORTED_YAHOO_INTERVALS = {"1d", "5d", "1wk", "1mo", "3mo"}
SUPPORTED_YAHOO_CACHE_FORMATS = {"csv", "parquet"}
DEMO_REFERENCE_MODE_WARNING = "Demo reference files are fake/sample data and are not suitable for production research."
DEMO_REFERENCE_PATHS = {
    "metadata_path": "data/reference/metadata_sample.csv",
    "sector_map_path": "data/reference/sector_map_sample.csv",
    "country_map_path": "data/reference/country_map_sample.csv",
    "thailand_universe_path": "data/reference/thailand/thailand_universe_sample.csv",
    "thailand_sector_map_path": "data/reference/thailand/thailand_sector_map_sample.csv",
    "thailand_security_types_path": "data/reference/thailand/thailand_security_types_sample.csv",
    "thailand_liquidity_path": "data/reference/thailand/thailand_liquidity_sample.csv",
    "thailand_dr_mapping_path": "data/reference/thailand/thailand_dr_mapping_sample.csv",
    "dr_market_data_path": "data/reference/thailand/dr_quality/dr_market_data_sample.csv",
    "dr_bid_ask_path": "data/reference/thailand/dr_quality/dr_bid_ask_sample.csv",
    "dr_fair_value_inputs_path": "data/reference/thailand/dr_quality/dr_fair_value_inputs_sample.csv",
    "fx_rates_path": "data/reference/thailand/dr_quality/fx_rates_sample.csv",
    "underlying_prices_path": "data/reference/thailand/dr_quality/underlying_prices_sample.csv",
}
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


def validate_yahoo_source_config(yahoo_config: dict) -> list[str]:
    """Validate Yahoo historical source settings without making network calls."""
    warnings: list[str] = []
    tickers = yahoo_config.get("tickers")
    if not isinstance(tickers, list) or not any(str(ticker).strip() for ticker in tickers):
        warnings.append("Yahoo config missing tickers: add at least one historical Yahoo ticker")
    elif any(not str(ticker).strip() for ticker in tickers):
        warnings.append("Yahoo config contains blank ticker entries")

    interval = yahoo_config.get("interval", "1d")
    if interval not in SUPPORTED_YAHOO_INTERVALS:
        warnings.append(f"Yahoo config unsupported interval: {interval}")

    cache_format = yahoo_config.get("cache_format", "parquet")
    if cache_format not in SUPPORTED_YAHOO_CACHE_FORMATS:
        warnings.append(f"Yahoo config unsupported cache_format: {cache_format}")

    cache_dir = yahoo_config.get("cache_dir")
    if not cache_dir or not str(cache_dir).strip():
        warnings.append("Yahoo config missing cache_dir")

    try:
        cache_ttl_hours = float(yahoo_config.get("cache_ttl_hours", 8))
        if cache_ttl_hours < 0:
            warnings.append("Yahoo config cache_ttl_hours must be non-negative")
    except (TypeError, ValueError):
        warnings.append("Yahoo config cache_ttl_hours must be numeric")

    if not isinstance(yahoo_config.get("fallback_to_cache", True), bool):
        warnings.append("Yahoo config fallback_to_cache must be true or false")

    period = yahoo_config.get("period")
    start = yahoo_config.get("start")
    end = yahoo_config.get("end")
    if not period and not start:
        warnings.append("Yahoo config should include period or start date")
    if period and start:
        warnings.append("Yahoo config has both period and start; start/end will override period")
    if start and end:
        start_date = pd.to_datetime(start, errors="coerce")
        end_date = pd.to_datetime(end, errors="coerce")
        if pd.isna(start_date):
            warnings.append(f"Yahoo config invalid start date: {start}")
        if pd.isna(end_date):
            warnings.append(f"Yahoo config invalid end date: {end}")
        if pd.notna(start_date) and pd.notna(end_date) and end_date <= start_date:
            warnings.append("Yahoo config end date must be after start date")

    reference_data = yahoo_config.get("reference_data") or {}
    for key, label in [
        ("metadata_path", "metadata"),
        ("sector_map_path", "sector map"),
        ("country_map_path", "country map"),
        ("dr_mapping_path", "DR mapping"),
    ]:
        value = reference_data.get(key)
        if not value:
            warnings.append(f"Yahoo config missing local {label} reference path")
        elif not Path(value).exists():
            warnings.append(f"Yahoo config local {label} reference path not found: {value}")
    return warnings


def apply_demo_reference_mode(config: dict, source_name: str | None = None) -> tuple[dict, list[str]]:
    """Map missing configured reference paths to bundled fake/demo sample files.

    The returned config is a runtime copy. The input config is never mutated and
    production paths that exist on disk are preserved.
    """
    result = deepcopy(config)
    active_source = source_name or result.get("active_source", "csv")
    settings = result.setdefault("source_settings", {}).setdefault(active_source, {})
    reference_data = settings.setdefault("reference_data", {})
    warnings = [DEMO_REFERENCE_MODE_WARNING]

    for key, demo_path in DEMO_REFERENCE_PATHS.items():
        current_path = reference_data.get(key)
        if current_path and Path(current_path).exists():
            continue
        if Path(demo_path).exists():
            reference_data[key] = demo_path
            warnings.append(f"Demo reference mode mapped {key} to {demo_path}")
    return result, warnings


def validate_data_sources_config(config: dict) -> list[str]:
    """Validate data source config with Yahoo-first checks when present."""
    warnings: list[str] = []
    source_settings = config.get("source_settings")
    if not isinstance(source_settings, dict):
        return ["Missing source_settings in data_sources config"]
    active_source = config.get("active_source")
    if active_source not in source_settings:
        warnings.append(f"active_source not found in source_settings: {active_source}")
    yahoo_settings = source_settings.get("yahoo")
    if isinstance(yahoo_settings, dict):
        warnings.extend(validate_yahoo_source_config(yahoo_settings))
    else:
        warnings.append("Yahoo source settings missing")
    return warnings
