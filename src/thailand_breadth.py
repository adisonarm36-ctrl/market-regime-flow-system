from __future__ import annotations

import pandas as pd

from .country_breadth import calculate_breadth_timeseries, latest_country_breadth


DEFAULT_EXCLUDED_TYPES = {"DR", "DRx", "DW", "ETF", "warrant"}


def apply_thai_liquidity_filter(
    metadata_df: pd.DataFrame,
    min_average_traded_value_20d: float = 0,
    value_column: str = "average_traded_value_20d",
) -> pd.Series:
    """Return a boolean mask for Thailand securities that pass the liquidity filter."""
    if value_column not in metadata_df.columns:
        return pd.Series(True, index=metadata_df.index)
    return metadata_df[value_column].fillna(0) >= min_average_traded_value_20d


def filter_thailand_domestic_universe(
    metadata_df: pd.DataFrame,
    universe: str | None = None,
    excluded_types: set[str] | None = None,
    min_average_traded_value_20d: float = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Filter Thailand domestic universe and return included and excluded metadata."""
    required = {"Ticker", "SecurityType"}
    if not required.issubset(metadata_df.columns):
        raise ValueError("metadata_df must include Ticker and SecurityType")

    excluded_types = excluded_types or DEFAULT_EXCLUDED_TYPES
    data = metadata_df.copy()
    included_mask = pd.Series(True, index=data.index)

    if universe is not None and "Universe" in data.columns:
        included_mask &= data["Universe"].eq(universe)

    security_type = data["SecurityType"].astype(str)
    excluded_type_mask = security_type.isin(excluded_types)
    suspended_mask = data["Suspended"].fillna(False).astype(bool) if "Suspended" in data.columns else pd.Series(False, index=data.index)
    liquidity_mask = apply_thai_liquidity_filter(data, min_average_traded_value_20d)

    included_mask &= ~excluded_type_mask
    included_mask &= ~suspended_mask
    included_mask &= liquidity_mask

    excluded = data[~included_mask].copy()
    excluded["exclusion_reason"] = ""
    excluded.loc[excluded_type_mask.loc[excluded.index], "exclusion_reason"] += "excluded_security_type;"
    excluded.loc[suspended_mask.loc[excluded.index], "exclusion_reason"] += "suspended;"
    excluded.loc[~liquidity_mask.loc[excluded.index], "exclusion_reason"] += "illiquid;"
    if universe is not None and "Universe" in data.columns:
        out_of_universe = ~data["Universe"].eq(universe)
        excluded.loc[out_of_universe.loc[excluded.index], "exclusion_reason"] += "outside_universe;"

    return data[included_mask].copy(), excluded


def excluded_securities_summary(excluded_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize excluded Thailand securities by exclusion reason."""
    if excluded_df.empty or "exclusion_reason" not in excluded_df.columns:
        return pd.DataFrame(columns=["exclusion_reason", "count"])

    rows = []
    for reason_text in excluded_df["exclusion_reason"]:
        for reason in [item for item in str(reason_text).split(";") if item]:
            rows.append(reason)
    if not rows:
        return pd.DataFrame(columns=["exclusion_reason", "count"])
    return pd.Series(rows).value_counts().rename_axis("exclusion_reason").reset_index(name="count")


def calculate_thai_market_breadth(
    price_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    universe: str = "SET ex-DR",
    min_average_traded_value_20d: float = 0,
) -> dict[str, pd.DataFrame]:
    """Calculate Thailand domestic breadth without mixing DRs or other excluded instruments."""
    included, excluded = filter_thailand_domestic_universe(
        metadata_df,
        universe=universe,
        min_average_traded_value_20d=min_average_traded_value_20d,
    )
    tickers = [ticker for ticker in included["Ticker"] if ticker in price_df.columns]

    if not tickers:
        return {
            "thailand_market_health": pd.DataFrame(
                [{"country": "Thailand", "universe": universe, "missing_data": "No eligible Thailand domestic tickers found in price data"}]
            ),
            "breadth_timeseries": pd.DataFrame(),
            "included_securities": included,
            "excluded_securities": excluded,
            "excluded_summary": excluded_securities_summary(excluded),
        }

    latest = latest_country_breadth(price_df[tickers], "Thailand")
    latest.insert(2, "universe", universe)
    return {
        "thailand_market_health": latest,
        "breadth_timeseries": calculate_breadth_timeseries(price_df[tickers]),
        "included_securities": included,
        "excluded_securities": excluded,
        "excluded_summary": excluded_securities_summary(excluded),
    }


def calculate_thai_sector_breadth(
    price_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    sector_column: str = "Sector",
    min_average_traded_value_20d: float = 0,
) -> pd.DataFrame:
    """Calculate latest Thailand domestic breadth by sector for eligible securities only."""
    if sector_column not in metadata_df.columns:
        raise ValueError(f"metadata_df must include {sector_column}")

    included, _ = filter_thailand_domestic_universe(
        metadata_df,
        universe=None,
        min_average_traded_value_20d=min_average_traded_value_20d,
    )
    summaries = []
    for sector, group in included.groupby(sector_column):
        tickers = [ticker for ticker in group["Ticker"] if ticker in price_df.columns]
        if not tickers:
            summaries.append({sector_column: sector, "missing_data": "No eligible tickers found in price data"})
            continue
        summary = latest_country_breadth(price_df[tickers], "Thailand").iloc[0].to_dict()
        summary[sector_column] = sector
        summaries.append(summary)
    return pd.DataFrame(summaries)
