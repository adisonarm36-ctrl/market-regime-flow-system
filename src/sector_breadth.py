from __future__ import annotations

import pandas as pd

from .country_breadth import calculate_breadth_timeseries


def _validate_metadata(metadata_df: pd.DataFrame, required_columns: set[str]) -> None:
    missing = required_columns.difference(metadata_df.columns)
    if missing:
        raise ValueError(f"metadata_df missing required columns: {', '.join(sorted(missing))}")


def aggregate_breadth_by_group(
    price_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    group_column: str,
    country: str | None = None,
) -> pd.DataFrame:
    """Aggregate latest breadth metrics by a metadata group such as sector or industry."""
    required = {"Ticker", group_column}
    if country is not None:
        required.add("Country")
    _validate_metadata(metadata_df, required)

    data = metadata_df.copy()
    if country is not None:
        data = data[data["Country"].eq(country)]

    rows: list[dict[str, object]] = []
    for group_name, group in data.dropna(subset=[group_column]).groupby(group_column):
        tickers = [ticker for ticker in group["Ticker"] if ticker in price_df.columns]
        if not tickers:
            rows.append({group_column: group_name, "missing_data": "No configured tickers found in price data"})
            continue

        breadth = calculate_breadth_timeseries(price_df[tickers])
        latest = breadth.iloc[-1].to_dict()
        latest[group_column] = group_name
        latest["as_of"] = breadth.index[-1]
        rows.append(latest)

    result = pd.DataFrame(rows)
    if result.empty or "breadth_score" not in result.columns:
        return result
    return result.sort_values("breadth_score", ascending=False).reset_index(drop=True)


def aggregate_breadth_by_country(price_df: pd.DataFrame, metadata_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate latest breadth metrics by country."""
    return aggregate_breadth_by_group(price_df, metadata_df, "Country")


def aggregate_breadth_by_sector(price_df: pd.DataFrame, metadata_df: pd.DataFrame, country: str | None = None) -> pd.DataFrame:
    """Aggregate latest breadth metrics by sector, optionally inside one country."""
    return aggregate_breadth_by_group(price_df, metadata_df, "Sector", country=country)


def aggregate_breadth_by_industry(price_df: pd.DataFrame, metadata_df: pd.DataFrame, country: str | None = None) -> pd.DataFrame:
    """Aggregate latest breadth metrics by industry, optionally inside one country."""
    return aggregate_breadth_by_group(price_df, metadata_df, "Industry", country=country)


def rank_strongest_sectors(sector_breadth_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Rank strongest sectors by breadth score."""
    return sector_breadth_df.dropna(subset=["breadth_score"]).sort_values("breadth_score", ascending=False).head(n).reset_index(drop=True)


def rank_weakest_sectors(sector_breadth_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Rank weakest sectors by breadth score."""
    return sector_breadth_df.dropna(subset=["breadth_score"]).sort_values("breadth_score", ascending=True).head(n).reset_index(drop=True)


def calculate_group_breadth_timeseries(
    price_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    group_column: str,
) -> pd.DataFrame:
    """Calculate breadth time series for each sector, industry, country, or custom group."""
    _validate_metadata(metadata_df, {"Ticker", group_column})
    frames: list[pd.DataFrame] = []

    for group_name, group in metadata_df.dropna(subset=[group_column]).groupby(group_column):
        tickers = [ticker for ticker in group["Ticker"] if ticker in price_df.columns]
        if not tickers:
            continue
        breadth = calculate_breadth_timeseries(price_df[tickers]).copy()
        breadth[group_column] = group_name
        frames.append(breadth.reset_index(names="Date"))

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def detect_improving_sectors(
    sector_breadth_timeseries: pd.DataFrame,
    group_column: str = "Sector",
    lookback: int = 20,
) -> pd.DataFrame:
    """Rank sectors whose breadth score improved most over a lookback window."""
    return _rank_breadth_change(sector_breadth_timeseries, group_column, lookback, ascending=False)


def detect_deteriorating_sectors(
    sector_breadth_timeseries: pd.DataFrame,
    group_column: str = "Sector",
    lookback: int = 20,
) -> pd.DataFrame:
    """Rank sectors whose breadth score deteriorated most over a lookback window."""
    return _rank_breadth_change(sector_breadth_timeseries, group_column, lookback, ascending=True)


def _rank_breadth_change(
    breadth_timeseries: pd.DataFrame,
    group_column: str,
    lookback: int,
    ascending: bool,
) -> pd.DataFrame:
    if breadth_timeseries.empty:
        return pd.DataFrame(columns=[group_column, "latest_score", "prior_score", "score_change"])
    required = {"Date", group_column, "breadth_score"}
    missing = required.difference(breadth_timeseries.columns)
    if missing:
        raise ValueError(f"breadth_timeseries missing required columns: {', '.join(sorted(missing))}")

    rows = []
    sorted_data = breadth_timeseries.sort_values(["Date", group_column])
    for group_name, group in sorted_data.groupby(group_column):
        group = group.sort_values("Date")
        if len(group) <= lookback:
            prior = group["breadth_score"].iloc[0]
        else:
            prior = group["breadth_score"].iloc[-lookback - 1]
        latest = group["breadth_score"].iloc[-1]
        rows.append({group_column: group_name, "latest_score": latest, "prior_score": prior, "score_change": latest - prior})

    return pd.DataFrame(rows).sort_values("score_change", ascending=ascending).reset_index(drop=True)
