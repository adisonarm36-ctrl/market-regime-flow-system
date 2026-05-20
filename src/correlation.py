from __future__ import annotations

import pandas as pd


def static_correlation_matrix(returns_df: pd.DataFrame, method: str = "pearson", min_periods: int = 2) -> pd.DataFrame:
    """Calculate a static return correlation matrix."""
    return returns_df.corr(method=method, min_periods=min_periods)


def rolling_correlation_matrix(returns_df: pd.DataFrame, window: int = 60, method: str = "pearson") -> pd.DataFrame:
    """Calculate rolling return correlation matrices as a pandas MultiIndex result."""
    if method != "pearson":
        raise ValueError("pandas rolling correlation supports pearson correlation only")
    return returns_df.rolling(window=window, min_periods=max(2, min(window, len(returns_df)))).corr()


def correlation_distance(correlation_df: pd.DataFrame) -> pd.DataFrame:
    """Convert correlation to distance using 1 - correlation."""
    return (1 - correlation_df).clip(lower=0, upper=2)


def latest_rolling_correlation(rolling_corr_df: pd.DataFrame) -> pd.DataFrame:
    """Extract the latest matrix from a rolling correlation result."""
    if not isinstance(rolling_corr_df.index, pd.MultiIndex):
        raise ValueError("rolling_corr_df must have a MultiIndex produced by rolling().corr()")
    latest_date = rolling_corr_df.index.get_level_values(0).max()
    return rolling_corr_df.loc[latest_date]
