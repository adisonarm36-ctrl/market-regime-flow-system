from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.thailand_breadth import filter_thailand_domestic_breadth_universe


YAHOO_TICKER_COLUMNS = ["YahooTicker", "Yahoo_Ticker", "YahooSymbol", "Yahoo_Symbol"]


@dataclass(frozen=True)
class YahooTickerUniverse:
    """Yahoo ticker selection built only from local reference fields."""

    yahoo_tickers: list[str]
    selected_reference: pd.DataFrame
    warnings: list[str]


def find_yahoo_ticker_column(reference_df: pd.DataFrame) -> str | None:
    """Return the first supported local Yahoo ticker field, if configured."""
    for column in YAHOO_TICKER_COLUMNS:
        if column in reference_df.columns:
            return column
    return None


def build_yahoo_ticker_universe(
    reference_df: pd.DataFrame,
    universe: str | None = None,
    yahoo_ticker_column: str | None = None,
) -> YahooTickerUniverse:
    """Build Yahoo tickers from local reference data without inventing mappings."""
    if reference_df.empty:
        return YahooTickerUniverse([], reference_df.copy(), ["Yahoo ticker universe skipped: reference data is empty"])
    if "Ticker" not in reference_df.columns:
        return YahooTickerUniverse([], reference_df.copy(), ["Yahoo ticker universe skipped: reference data missing Ticker"])

    selected = reference_df.copy()
    if universe is not None and "Universe" in selected.columns:
        selected = selected[selected["Universe"].astype(str).str.strip().eq(universe)].copy()

    column = yahoo_ticker_column or find_yahoo_ticker_column(selected)
    if column is None:
        return YahooTickerUniverse(
            [],
            selected,
            ["Yahoo ticker format missing: add one of YahooTicker, Yahoo_Ticker, YahooSymbol, Yahoo_Symbol to local reference data"],
        )

    values = selected[column].astype("string").str.strip()
    missing_rows = selected[values.isna() | values.eq("")]
    warnings = []
    if not missing_rows.empty:
        warnings.append(f"Yahoo ticker format missing for local tickers: {', '.join(missing_rows['Ticker'].astype(str).tolist())}")

    yahoo_tickers = values[values.notna() & values.ne("")].drop_duplicates().tolist()
    if not yahoo_tickers:
        warnings.append("Yahoo ticker universe skipped: no populated Yahoo ticker values")
    return YahooTickerUniverse(yahoo_tickers, selected, warnings)


def build_thailand_domestic_yahoo_ticker_universe(
    thailand_metadata_df: pd.DataFrame,
    liquidity_df: pd.DataFrame | None = None,
    universe: str | None = "SET ex-DR",
    min_avg_value_20d: float | None = None,
    min_trading_days_ratio_60d: float | None = None,
    yahoo_ticker_column: str | None = None,
) -> YahooTickerUniverse:
    """Build Yahoo tickers from Thailand domestic breadth-eligible local reference rows."""
    eligibility = filter_thailand_domestic_breadth_universe(
        metadata_df=thailand_metadata_df,
        liquidity_df=liquidity_df,
        universe=universe,
        min_avg_value_20d=min_avg_value_20d,
        min_trading_days_ratio_60d=min_trading_days_ratio_60d,
    )
    result = build_yahoo_ticker_universe(
        eligibility["included_securities"],
        universe=None,
        yahoo_ticker_column=yahoo_ticker_column,
    )
    warnings = list(result.warnings)
    excluded = eligibility["excluded_securities"]
    if not excluded.empty:
        warnings.append(f"Thailand domestic Yahoo universe excluded {len(excluded)} non-eligible local rows")
    return YahooTickerUniverse(result.yahoo_tickers, result.selected_reference, warnings)
