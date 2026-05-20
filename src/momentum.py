from __future__ import annotations

import numpy as np
import pandas as pd

from .country_breadth import distance_from_52week_high


MOMENTUM_WINDOWS = {
    "momentum_1m": 21,
    "momentum_3m": 63,
    "momentum_6m": 126,
    "momentum_12m": 252,
}


def calculate_momentum(price_df: pd.DataFrame, window: int) -> pd.Series:
    """Calculate latest point-to-point momentum for each ticker."""
    return price_df.sort_index().pct_change(window).iloc[-1]


def volatility_adjusted_momentum(price_df: pd.DataFrame, momentum_window: int = 126, volatility_window: int = 126) -> pd.Series:
    """Calculate latest volatility-adjusted momentum."""
    prices = price_df.sort_index()
    momentum = prices.pct_change(momentum_window).iloc[-1]
    volatility = prices.pct_change().rolling(volatility_window, min_periods=2).std().iloc[-1] * np.sqrt(252)
    return (momentum / volatility.replace(0, np.nan)).rename("volatility_adjusted_momentum")


def moving_average_trend_filter(price_df: pd.DataFrame, short_window: int = 50, long_window: int = 200) -> pd.DataFrame:
    """Calculate latest 50MA/200MA trend filter metrics."""
    prices = price_df.sort_index()
    short_ma = prices.rolling(short_window, min_periods=1).mean().iloc[-1]
    long_ma = prices.rolling(long_window, min_periods=1).mean().iloc[-1]
    latest = prices.iloc[-1]
    return pd.DataFrame(
        {
            "Ticker": prices.columns,
            "above_50ma": latest.gt(short_ma).values,
            "above_200ma": latest.gt(long_ma).values,
            "trend_quality": latest.gt(short_ma).astype(int).add(latest.gt(long_ma).astype(int)).values,
        }
    )


def calculate_momentum_table(price_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate multi-horizon momentum, 52-week high distance, and trend filters."""
    prices = price_df.sort_index()
    table = pd.DataFrame(index=prices.columns)
    for column, window in MOMENTUM_WINDOWS.items():
        table[column] = calculate_momentum(prices, window)
    table["volatility_adjusted_momentum"] = volatility_adjusted_momentum(prices)
    table["distance_from_52week_high"] = distance_from_52week_high(prices).iloc[-1]
    table = table.reset_index(names="Ticker").merge(moving_average_trend_filter(prices), on="Ticker", how="left")
    table["momentum_score"] = _score_momentum_table(table)
    return table.sort_values("momentum_score", ascending=False).reset_index(drop=True)


def rank_momentum(momentum_df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Rank instruments by momentum score."""
    return momentum_df.sort_values("momentum_score", ascending=False).head(n).reset_index(drop=True)


def _score_momentum_table(table: pd.DataFrame) -> pd.Series:
    components = []
    for column in [*MOMENTUM_WINDOWS.keys(), "volatility_adjusted_momentum"]:
        components.append(table[column].rank(pct=True) * 100)
    components.append((table["distance_from_52week_high"].rank(pct=True) * 100))
    components.append(table["trend_quality"] / 2 * 100)
    return pd.concat(components, axis=1).mean(axis=1, skipna=True).fillna(0)
