from __future__ import annotations

import pandas as pd

from .breadth_regime import classify_regime


TRADING_DAYS_52W = 252


def rolling_52week_high(price_df: pd.DataFrame, window: int = TRADING_DAYS_52W) -> pd.DataFrame:
    """Calculate rolling 52-week high using 252 trading days by default."""
    return price_df.sort_index().rolling(window=window, min_periods=1).max()


def rolling_52week_low(price_df: pd.DataFrame, window: int = TRADING_DAYS_52W) -> pd.DataFrame:
    """Calculate rolling 52-week low using 252 trading days by default."""
    return price_df.sort_index().rolling(window=window, min_periods=1).min()


def distance_from_52week_high(price_df: pd.DataFrame, window: int = TRADING_DAYS_52W) -> pd.DataFrame:
    """Calculate percentage distance from rolling 52-week high."""
    high = rolling_52week_high(price_df, window)
    return price_df.sort_index() / high - 1


def percent_within_high(distance_df: pd.DataFrame, threshold: float) -> pd.Series:
    """Calculate percent of instruments within a threshold from 52-week high."""
    return distance_df.ge(-abs(threshold)).mean(axis=1) * 100


def percent_down_more_than(distance_df: pd.DataFrame, threshold: float) -> pd.Series:
    """Calculate percent of instruments down more than a threshold from 52-week high."""
    return distance_df.le(-abs(threshold)).mean(axis=1) * 100


def percent_above_moving_average(price_df: pd.DataFrame, window: int) -> pd.Series:
    """Calculate percent of instruments above a moving average."""
    sorted_prices = price_df.sort_index()
    moving_average = sorted_prices.rolling(window=window, min_periods=1).mean()
    return sorted_prices.gt(moving_average).mean(axis=1) * 100


def new_52week_highs(price_df: pd.DataFrame, window: int = TRADING_DAYS_52W) -> pd.Series:
    """Count instruments making a new rolling 52-week high."""
    sorted_prices = price_df.sort_index()
    high = rolling_52week_high(sorted_prices, window)
    return sorted_prices.eq(high).sum(axis=1)


def new_52week_lows(price_df: pd.DataFrame, window: int = TRADING_DAYS_52W) -> pd.Series:
    """Count instruments making a new rolling 52-week low."""
    sorted_prices = price_df.sort_index()
    low = rolling_52week_low(sorted_prices, window)
    return sorted_prices.eq(low).sum(axis=1)


def calculate_breadth_timeseries(price_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate country breadth metrics through time for a price universe."""
    distance = distance_from_52week_high(price_df)
    breadth = pd.DataFrame(index=price_df.sort_index().index)
    breadth["pct_within_5pct_high"] = percent_within_high(distance, 0.05)
    breadth["pct_within_10pct_high"] = percent_within_high(distance, 0.10)
    breadth["pct_down_more_20pct"] = percent_down_more_than(distance, 0.20)
    breadth["pct_down_more_30pct"] = percent_down_more_than(distance, 0.30)
    breadth["pct_above_50ma"] = percent_above_moving_average(price_df, 50)
    breadth["pct_above_200ma"] = percent_above_moving_average(price_df, 200)
    breadth["new_52week_highs"] = new_52week_highs(price_df)
    breadth["new_52week_lows"] = new_52week_lows(price_df)
    breadth["instrument_count"] = price_df.notna().sum(axis=1)
    breadth["breadth_score"] = calculate_breadth_score(breadth)
    breadth["regime"] = breadth["breadth_score"].map(classify_regime)
    return breadth


def calculate_breadth_score(breadth_df: pd.DataFrame) -> pd.Series:
    """Calculate a 0-100 market breadth score from breadth buckets."""
    positive = (
        breadth_df["pct_within_5pct_high"] * 0.25
        + breadth_df["pct_within_10pct_high"] * 0.20
        + breadth_df["pct_above_50ma"] * 0.25
        + breadth_df["pct_above_200ma"] * 0.20
    )
    negative = breadth_df["pct_down_more_20pct"] * 0.06 + breadth_df["pct_down_more_30pct"] * 0.04
    return (positive - negative).clip(lower=0, upper=100)


def latest_country_breadth(price_df: pd.DataFrame, country: str) -> pd.DataFrame:
    """Return the latest country-level breadth summary."""
    breadth = calculate_breadth_timeseries(price_df)
    latest = breadth.iloc[-1].to_frame().T
    latest.insert(0, "country", country)
    latest.insert(1, "as_of", breadth.index[-1])
    return latest.reset_index(drop=True)


def calculate_country_breadth(price_df: pd.DataFrame, country_map: pd.DataFrame) -> pd.DataFrame:
    """Calculate latest breadth summary for each country using a Ticker/Country map."""
    if not {"Ticker", "Country"}.issubset(country_map.columns):
        raise ValueError("country_map must include Ticker and Country")

    summaries = []
    for country, group in country_map.groupby("Country"):
        tickers = [ticker for ticker in group["Ticker"] if ticker in price_df.columns]
        if not tickers:
            summaries.append({"country": country, "missing_data": "No configured tickers found in price data"})
            continue
        summaries.append(latest_country_breadth(price_df[tickers], str(country)).iloc[0].to_dict())

    return pd.DataFrame(summaries)
