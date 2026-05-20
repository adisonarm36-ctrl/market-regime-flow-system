from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config_loader import load_yaml


REQUIRED_DR_MAPPING_COLUMNS = ["DR_Ticker", "Underlying_Ticker"]


def load_dr_mapping(path: str | Path) -> pd.DataFrame:
    """Load DR-to-underlying mapping from a YAML config file."""
    config = load_yaml(path)
    rows = config.get("dr_mappings", [])
    return pd.DataFrame(rows)


def validate_dr_mapping(mapping_df: pd.DataFrame) -> list[str]:
    """Validate required DR mapping fields and duplicate DR tickers."""
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
    errors = validate_dr_mapping(dr_mapping_df)
    if errors:
        raise ValueError("; ".join(errors))
    if signal_ticker_column not in signal_df.columns:
        raise ValueError(f"signal_df must include {signal_ticker_column}")

    signal = signal_df.rename(columns={signal_ticker_column: "Underlying_Ticker"})
    merged = dr_mapping_df.merge(signal, on="Underlying_Ticker", how="left", indicator=True)
    merged["signal_status"] = merged["_merge"].map({"both": "available", "left_only": "missing_underlying_signal", "right_only": "unexpected"})
    return merged.drop(columns=["_merge"])
