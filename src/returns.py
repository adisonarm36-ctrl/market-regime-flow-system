from __future__ import annotations

import numpy as np
import pandas as pd


def simple_returns(price_df: pd.DataFrame, periods: int = 1) -> pd.DataFrame:
    """Calculate simple returns from a Date x Ticker price table."""
    return price_df.sort_index().pct_change(periods=periods)


def log_returns(price_df: pd.DataFrame, periods: int = 1) -> pd.DataFrame:
    """Calculate log returns from a Date x Ticker price table."""
    sorted_prices = price_df.sort_index()
    return np.log(sorted_prices / sorted_prices.shift(periods))


def window_return(price_df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Calculate point-to-point simple return over a window."""
    return simple_returns(price_df, periods=window)
