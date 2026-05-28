from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.config_loader import load_yaml


REQUIRED_METADATA_COLUMNS = ["Ticker", "SecurityType", "Country", "Sector", "Industry", "Universe", "Suspended"]
OPTIONAL_METADATA_COLUMNS = ["Name", "Currency", "Exchange", "IsDR", "UnderlyingTicker", "average_traded_value_20d", "Notes"]


def load_metadata(path: str | Path) -> pd.DataFrame:
    """Load and validate local metadata reference data."""
    df = _load_tabular_reference(path)
    validate_metadata_schema(df)
    return df


def load_sector_map(path: str | Path) -> pd.DataFrame:
    """Load and validate local sector map reference data."""
    df = _load_tabular_reference(path)
    validate_sector_map_schema(df)
    return df


def load_country_map(path: str | Path) -> pd.DataFrame:
    """Load and validate local country map reference data."""
    df = _load_tabular_reference(path)
    validate_country_map_schema(df)
    return df


def load_asset_map(path: str | Path) -> pd.DataFrame:
    """Load local asset map reference data from CSV or simple YAML mapping."""
    return _load_tabular_reference(path)


def load_dr_mapping(path: str | Path) -> pd.DataFrame:
    """Load local DR mapping reference data from CSV or YAML."""
    df = _load_tabular_reference(path)
    df = _normalize_dr_mapping_aliases(df)
    missing = {"DR_Ticker", "Underlying_Ticker"}.difference(df.columns)
    if missing:
        raise ValueError(f"Missing DR mapping columns: {', '.join(sorted(missing))}")
    return df


def validate_metadata_schema(metadata_df: pd.DataFrame) -> None:
    """Raise a clear validation error for missing required metadata columns."""
    missing = [column for column in REQUIRED_METADATA_COLUMNS if column not in metadata_df.columns]
    if missing:
        raise ValueError(f"Missing required metadata columns: {', '.join(missing)}")


def validate_sector_map_schema(sector_df: pd.DataFrame) -> None:
    """Validate sector map schema."""
    missing = {"Ticker", "Sector"}.difference(sector_df.columns)
    if missing:
        raise ValueError(f"Missing sector map columns: {', '.join(sorted(missing))}")


def validate_country_map_schema(country_df: pd.DataFrame) -> None:
    """Validate country map schema."""
    missing = {"Ticker", "Country"}.difference(country_df.columns)
    if missing:
        raise ValueError(f"Missing country map columns: {', '.join(sorted(missing))}")


def merge_reference_data(
    price_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    sector_df: pd.DataFrame | None = None,
    country_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Merge available reference data and flag price tickers without metadata."""
    validate_metadata_schema(metadata_df)
    tickers = pd.DataFrame({"Ticker": list(price_df.columns)})
    merged = tickers.merge(metadata_df, on="Ticker", how="left", indicator=True)
    warnings: list[str] = []
    missing = merged.loc[merged["_merge"].eq("left_only"), "Ticker"].tolist()
    if missing:
        warnings.append(f"tickers missing metadata: {', '.join(missing)}")
    merged["missing_metadata"] = merged["_merge"].eq("left_only")
    merged = merged.drop(columns=["_merge"])

    if sector_df is not None and not sector_df.empty:
        validate_sector_map_schema(sector_df)
        merged = _fill_reference_columns(merged, sector_df, ["Sector"])
    if country_df is not None and not country_df.empty:
        validate_country_map_schema(country_df)
        merged = _fill_reference_columns(merged, country_df, ["Country"])
    return merged, warnings


def _fill_reference_columns(base: pd.DataFrame, reference: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    suffix = "_ref"
    result = base.merge(reference[["Ticker", *columns]], on="Ticker", how="left", suffixes=("", suffix))
    for column in columns:
        ref_column = f"{column}{suffix}"
        if ref_column in result.columns:
            result[column] = result[column].where(result[column].notna(), result[ref_column])
            result = result.drop(columns=[ref_column])
    return result


def _load_tabular_reference(path: str | Path) -> pd.DataFrame:
    ref_path = Path(path)
    if not str(path):
        raise FileNotFoundError("reference path is blank")
    if not ref_path.exists():
        raise FileNotFoundError(f"reference path not found: {ref_path}")
    if ref_path.suffix.lower() in {".yaml", ".yml"}:
        loaded = load_yaml(ref_path)
        return _yaml_to_dataframe(loaded)
    return pd.read_csv(ref_path)


def _yaml_to_dataframe(loaded: dict[str, Any]) -> pd.DataFrame:
    for key in ["dr_mappings", "asset_mappings", "sector_mappings", "country_mappings"]:
        if isinstance(loaded.get(key), list):
            return pd.DataFrame(loaded[key])
    if all(isinstance(value, dict) for value in loaded.values()):
        rows = []
        for group_name, mapping in loaded.items():
            for ticker, value in mapping.items():
                rows.append({"Ticker": ticker, group_name.rstrip("s"): value})
        return pd.DataFrame(rows)
    return pd.DataFrame()


def _normalize_dr_mapping_aliases(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    aliases = {
        "DRTicker": "DR_Ticker",
        "UnderlyingTicker": "Underlying_Ticker",
    }
    for source, target in aliases.items():
        if source in result.columns and target not in result.columns:
            result[target] = result[source]
    if "Underlying_Ticker" in result.columns and "UnderlyingTicker" not in result.columns:
        result["UnderlyingTicker"] = result["Underlying_Ticker"]
    return result
