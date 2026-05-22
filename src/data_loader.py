from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data_validation import REQUIRED_OHLCV_COLUMNS, validate_ohlcv


ADJUSTED_CLOSE_COLUMNS = ["Adjusted Close", "Adj Close"]


def load_ohlcv_csv(path: str | Path, validate: bool = True) -> pd.DataFrame:
    """Load OHLCV market data from CSV with Date parsed as datetime."""
    if validate:
        from .data_adapters.csv_adapter import CsvDataAdapter

        return CsvDataAdapter(price_path=path).load_prices()

    df = pd.read_csv(path)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])

    if validate:
        result = validate_ohlcv(df)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))

    return df.sort_values(["Date", "Ticker"]).reset_index(drop=True)


def get_price_column(df: pd.DataFrame, prefer_adjusted: bool = True) -> str:
    """Return the preferred price column, using adjusted close when available."""
    if prefer_adjusted:
        for column in ADJUSTED_CLOSE_COLUMNS:
            if column in df.columns:
                return column
    return "Close"


def pivot_prices(df: pd.DataFrame, prefer_adjusted: bool = True) -> pd.DataFrame:
    """Pivot OHLCV data into Date x Ticker price format."""
    missing = [column for column in REQUIRED_OHLCV_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    price_column = get_price_column(df, prefer_adjusted)
    return (
        df.pivot(index="Date", columns="Ticker", values=price_column)
        .sort_index()
        .rename_axis(index="Date", columns="Ticker")
    )


def pivot_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot OHLCV data into Date x Ticker volume format."""
    missing = [column for column in ("Date", "Ticker", "Volume") if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return df.pivot(index="Date", columns="Ticker", values="Volume").sort_index()


def filter_tickers(df: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Filter long-form OHLCV rows to a configured ticker list."""
    if not tickers:
        return df.iloc[0:0].copy()
    return df[df["Ticker"].isin(tickers)].copy()
