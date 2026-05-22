from __future__ import annotations

import pandas as pd

from .country_breadth import calculate_breadth_timeseries, latest_country_breadth


DEFAULT_EXCLUDED_TYPES = {"DR", "DRx", "DW", "ETF", "warrant"}
DOMESTIC_STOCK_TYPES = {"Common Stock", "Stock", "Domestic Stock"}
EXCLUSION_FLAG_COLUMNS = ["IsDR", "IsDRx", "IsETF", "IsDW", "IsWarrant"]


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


def filter_thailand_domestic_breadth_universe(
    metadata_df: pd.DataFrame,
    liquidity_df: pd.DataFrame | None = None,
    universe: str | None = None,
    min_avg_value_20d: float | None = None,
    min_trading_days_ratio_60d: float | None = None,
) -> dict[str, object]:
    """Build an auditable Thailand domestic breadth universe from local reference data."""
    required = {"Ticker", "SecurityType"}
    if not required.issubset(metadata_df.columns):
        raise ValueError("metadata_df must include Ticker and SecurityType")

    data = metadata_df.copy()
    if liquidity_df is not None and not liquidity_df.empty:
        liquidity_columns = [
            column
            for column in ["Ticker", "average_traded_value_20d", "average_volume_20d", "trading_days_ratio_60d", "liquidity_bucket"]
            if column in liquidity_df.columns
        ]
        data = data.merge(liquidity_df[liquidity_columns], on="Ticker", how="left", suffixes=("", "_liquidity"))

    reasons = pd.Series("", index=data.index, dtype="object")
    include_mask = pd.Series(True, index=data.index)

    def exclude(mask: pd.Series, reason: str) -> None:
        nonlocal include_mask, reasons
        mask = mask.fillna(False)
        include_mask &= ~mask
        reasons.loc[mask] = reasons.loc[mask].map(lambda value: f"{value};{reason}" if value else reason)

    if "Country" in data.columns:
        exclude(~data["Country"].astype(str).str.strip().eq("Thailand"), "not_thailand")
    if universe is not None and "Universe" in data.columns:
        normalized_universe = "SET ex-DR" if universe == "SET_ex_DR" else universe
        exclude(~data["Universe"].astype(str).str.strip().eq(normalized_universe), "outside_universe")

    security_type = data["SecurityType"].astype(str).str.strip()
    exclude(~security_type.isin(DOMESTIC_STOCK_TYPES), "non_domestic_security_type")

    for column in EXCLUSION_FLAG_COLUMNS:
        if column in data.columns:
            exclude(_as_bool(data[column]), column.lower())

    if "Suspended" in data.columns:
        exclude(_as_bool(data["Suspended"]), "suspended")
    if "IncludeInDomesticBreadth" in data.columns:
        exclude(~_as_bool(data["IncludeInDomesticBreadth"]).fillna(False), "not_included_by_reference")

    if min_avg_value_20d is not None and "average_traded_value_20d" in data.columns:
        values = pd.to_numeric(data["average_traded_value_20d"], errors="coerce")
        exclude(values.isna() | values.lt(float(min_avg_value_20d)), "illiquid_avg_value_20d")
    if min_trading_days_ratio_60d is not None and "trading_days_ratio_60d" in data.columns:
        ratios = pd.to_numeric(data["trading_days_ratio_60d"], errors="coerce")
        exclude(ratios.isna() | ratios.lt(float(min_trading_days_ratio_60d)), "illiquid_trading_days_ratio_60d")

    included = data.loc[include_mask].copy()
    excluded = data.loc[~include_mask].copy()
    excluded["ExclusionReason"] = reasons.loc[~include_mask].str.strip(";")
    excluded["exclusion_reason"] = excluded["ExclusionReason"]
    report = pd.DataFrame(
        [
            {
                "selected_universe": universe or "All",
                "included_count": int(include_mask.sum()),
                "excluded_count": int((~include_mask).sum()),
                "min_avg_value_20d": min_avg_value_20d,
                "min_trading_days_ratio_60d": min_trading_days_ratio_60d,
            }
        ]
    )
    reason_breakdown = excluded_securities_summary(excluded)
    if not reason_breakdown.empty:
        report = report.merge(reason_breakdown.assign(key=1), how="cross") if hasattr(report, "merge") else report
    return {
        "included_tickers": included["Ticker"].tolist(),
        "excluded_tickers": excluded[["Ticker", "ExclusionReason"]] if not excluded.empty else pd.DataFrame(columns=["Ticker", "ExclusionReason"]),
        "eligibility_report": report,
        "included_securities": included,
        "excluded_securities": excluded,
        "exclusion_reason_breakdown": reason_breakdown,
    }


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
    liquidity_df: pd.DataFrame | None = None,
    min_trading_days_ratio_60d: float | None = None,
) -> dict[str, pd.DataFrame]:
    """Calculate Thailand domestic breadth without mixing DRs or other excluded instruments."""
    eligibility = filter_thailand_domestic_breadth_universe(
        metadata_df=metadata_df,
        liquidity_df=liquidity_df,
        universe=universe,
        min_avg_value_20d=min_average_traded_value_20d,
        min_trading_days_ratio_60d=min_trading_days_ratio_60d,
    )
    included = eligibility["included_securities"]
    excluded = eligibility["excluded_securities"]
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
            "thailand_eligibility_report": eligibility["eligibility_report"],
        }

    latest = latest_country_breadth(price_df[tickers], "Thailand")
    latest.insert(2, "universe", universe)
    return {
        "thailand_market_health": latest,
        "breadth_timeseries": calculate_breadth_timeseries(price_df[tickers]),
        "included_securities": included,
        "excluded_securities": excluded,
        "excluded_summary": excluded_securities_summary(excluded),
        "thailand_eligibility_report": eligibility["eligibility_report"],
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


def _as_bool(series: pd.Series) -> pd.Series:
    if str(series.dtype) == "boolean":
        return series.fillna(False).astype(bool)
    if series.dtype == bool:
        return series.fillna(False)
    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
        "y": True,
        "n": False,
    }
    return series.map(lambda value: mapping.get(str(value).strip().lower(), False) if pd.notna(value) else False)
