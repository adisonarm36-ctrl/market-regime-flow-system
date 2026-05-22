from __future__ import annotations

import pandas as pd


def summarize_reference_data_quality(price_df: pd.DataFrame, metadata_df: pd.DataFrame | None, dr_mapping_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Summarize reference data coverage for price tickers."""
    price_tickers = set(price_df.columns)
    metadata_tickers = set(metadata_df["Ticker"]) if metadata_df is not None and "Ticker" in metadata_df.columns else set()
    missing_metadata = sorted(price_tickers - metadata_tickers)
    metadata_count = len(metadata_tickers)
    price_count = len(price_tickers)
    return pd.DataFrame(
        [
            {
                "price_ticker_count": price_count,
                "metadata_ticker_count": metadata_count,
                "metadata_coverage_pct": (price_count - len(missing_metadata)) / price_count * 100 if price_count else 0,
                "tickers_missing_metadata": ", ".join(missing_metadata),
                "dr_mapping_count": 0 if dr_mapping_df is None or dr_mapping_df.empty else len(dr_mapping_df),
            }
        ]
    )


def summarize_ticker_metadata_coverage(price_df: pd.DataFrame, metadata_df: pd.DataFrame | None) -> pd.DataFrame:
    """Return per-ticker metadata coverage flags."""
    if metadata_df is not None and {"Ticker", "missing_metadata"}.issubset(metadata_df.columns):
        coverage = metadata_df[["Ticker", "missing_metadata"]].copy()
        coverage["has_metadata"] = ~coverage["missing_metadata"].fillna(False).astype(bool)
        return coverage[["Ticker", "has_metadata"]]
    metadata_tickers = set(metadata_df["Ticker"]) if metadata_df is not None and "Ticker" in metadata_df.columns else set()
    return pd.DataFrame(
        [{"Ticker": ticker, "has_metadata": ticker in metadata_tickers} for ticker in price_df.columns]
    )


def summarize_layer_availability(outputs: dict[str, pd.DataFrame], warnings: list[str] | None = None) -> pd.DataFrame:
    """Summarize whether report layers are available or skipped."""
    warnings = warnings or []
    layer_map = {
        "global_flow_summary": "Global Flow",
        "country_breadth_summary": "Country Breadth",
        "thailand_market_health": "Thailand Market Health",
        "sector_breadth_summary": "Sector Breadth",
        "cluster_summary": "Correlation Cluster",
        "stock_ranking": "Stock Ranking",
        "dr_quality_ranking": "DR Quality",
        "redundancy_report": "Redundancy",
    }
    rows = []
    for key, label in layer_map.items():
        table = outputs.get(key, pd.DataFrame())
        available = isinstance(table, pd.DataFrame) and not table.empty
        rows.append({"layer": label, "available": available, "reason": "" if available else _reason_for_layer(key, warnings)})
    return pd.DataFrame(rows)


def summarize_thailand_reference_quality(
    universe_df: pd.DataFrame | None = None,
    sector_map_df: pd.DataFrame | None = None,
    security_types_df: pd.DataFrame | None = None,
    liquidity_df: pd.DataFrame | None = None,
    dr_mapping_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Summarize local Thailand reference file coverage and row counts."""
    rows = []
    for name, df in [
        ("thailand_universe", universe_df),
        ("thailand_sector_map", sector_map_df),
        ("thailand_security_types", security_types_df),
        ("thailand_liquidity", liquidity_df),
        ("thailand_dr_mapping", dr_mapping_df),
    ]:
        warnings = getattr(df, "attrs", {}).get("warnings", []) if df is not None else []
        rows.append(
            {
                "reference_file": name,
                "loaded": df is not None and not df.empty,
                "row_count": 0 if df is None else len(df),
                "schema_warnings": "; ".join(warnings),
            }
        )
    return pd.DataFrame(rows)


def summarize_thailand_breadth_eligibility(eligibility_result: dict[str, object] | None) -> pd.DataFrame:
    """Summarize Thailand domestic breadth eligibility output."""
    if not eligibility_result:
        return pd.DataFrame(
            [{"domestic_eligible_count": 0, "excluded_count": 0, "excluded_count_by_reason": "", "missing_liquidity_count": 0}]
        )
    included = eligibility_result.get("included_securities", pd.DataFrame())
    excluded = eligibility_result.get("excluded_securities", pd.DataFrame())
    breakdown = eligibility_result.get("exclusion_reason_breakdown", pd.DataFrame())
    missing_liquidity_count = 0
    if isinstance(included, pd.DataFrame) and "average_traded_value_20d" in included.columns:
        missing_liquidity_count += int(included["average_traded_value_20d"].isna().sum())
    if isinstance(excluded, pd.DataFrame) and "average_traded_value_20d" in excluded.columns:
        missing_liquidity_count += int(excluded["average_traded_value_20d"].isna().sum())
    reason_text = ""
    if isinstance(breakdown, pd.DataFrame) and not breakdown.empty:
        reason_text = "; ".join(
            f"{row['exclusion_reason']}:{row['count']}" for _, row in breakdown.iterrows()
        )
    return pd.DataFrame(
        [
            {
                "domestic_eligible_count": 0 if not isinstance(included, pd.DataFrame) else len(included),
                "excluded_count": 0 if not isinstance(excluded, pd.DataFrame) else len(excluded),
                "excluded_count_by_reason": reason_text,
                "missing_liquidity_count": missing_liquidity_count,
            }
        ]
    )


def summarize_thailand_dr_mapping_quality(dr_mapping_df: pd.DataFrame | None) -> pd.DataFrame:
    """Summarize Thailand DR/DRx local mapping quality."""
    if dr_mapping_df is None or dr_mapping_df.empty:
        return pd.DataFrame(
            [{"dr_count": 0, "drx_count": 0, "active_count": 0, "inactive_count": 0, "duplicate_underlying_count": 0, "missing_underlying_count": 0}]
        )
    data = dr_mapping_df.copy()
    underlying_column = "UnderlyingTicker" if "UnderlyingTicker" in data.columns else "Underlying_Ticker"
    active = _bool_series(data["IsActive"]) if "IsActive" in data.columns else pd.Series(True, index=data.index)
    duplicate_count = int(data[underlying_column].value_counts().gt(1).sum()) if underlying_column in data.columns else 0
    missing_underlying = int(data[underlying_column].isna().sum()) if underlying_column in data.columns else len(data)
    return pd.DataFrame(
        [
            {
                "dr_count": int(data.get("DR_Type", pd.Series(dtype="object")).astype(str).eq("DR").sum()),
                "drx_count": int(data.get("DR_Type", pd.Series(dtype="object")).astype(str).eq("DRx").sum()),
                "active_count": int(active.sum()),
                "inactive_count": int((~active).sum()),
                "duplicate_underlying_count": duplicate_count,
                "missing_underlying_count": missing_underlying,
            }
        ]
    )


def _reason_for_layer(key: str, warnings: list[str]) -> str:
    matches = [warning for warning in warnings if key.split("_")[0] in warning.lower()]
    return "; ".join(matches) if matches else "missing optional data or no supported input"


def _bool_series(series: pd.Series) -> pd.Series:
    if str(series.dtype) == "boolean":
        return series.fillna(False).astype(bool)
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin(["true", "1", "yes", "y"])
