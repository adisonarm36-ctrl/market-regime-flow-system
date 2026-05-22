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


def _reason_for_layer(key: str, warnings: list[str]) -> str:
    matches = [warning for warning in warnings if key.split("_")[0] in warning.lower()]
    return "; ".join(matches) if matches else "missing optional data or no supported input"


def summarize_dr_execution_quality_data(dr_exec_df: pd.DataFrame | None) -> pd.DataFrame:
    """Summarize execution quality status statistics across all DRs."""
    if dr_exec_df is None or dr_exec_df.empty:
        return pd.DataFrame([{
            "total_dr_mapped": 0,
            "liquidity_supported_count": 0,
            "spread_supported_count": 0,
            "fair_value_supported_count": 0,
            "tracking_supported_count": 0,
            "execution_ready_count": 0,
            "confidence_high_count": 0,
            "confidence_medium_count": 0,
            "confidence_low_count": 0,
        }])
        
    return pd.DataFrame([{
        "total_dr_mapped": len(dr_exec_df),
        "liquidity_supported_count": int(dr_exec_df["LiquiditySupported"].sum()) if "LiquiditySupported" in dr_exec_df.columns else 0,
        "spread_supported_count": int(dr_exec_df["SpreadSupported"].sum()) if "SpreadSupported" in dr_exec_df.columns else 0,
        "fair_value_supported_count": int(dr_exec_df["FairValueSupported"].sum()) if "FairValueSupported" in dr_exec_df.columns else 0,
        "tracking_supported_count": int(dr_exec_df["TrackingSupported"].sum()) if "TrackingSupported" in dr_exec_df.columns else 0,
        "execution_ready_count": int((dr_exec_df["quality_label"] == "Execution Ready").sum()) if "quality_label" in dr_exec_df.columns else 0,
        "confidence_high_count": int((dr_exec_df["confidence_level"] == "High").sum()) if "confidence_level" in dr_exec_df.columns else 0,
        "confidence_medium_count": int((dr_exec_df["confidence_level"] == "Medium").sum()) if "confidence_level" in dr_exec_df.columns else 0,
        "confidence_low_count": int((dr_exec_df["confidence_level"] == "Low").sum()) if "confidence_level" in dr_exec_df.columns else 0,
    }])


def summarize_dr_fair_value_coverage(dr_exec_df: pd.DataFrame | None) -> pd.DataFrame:
    """Return ticker-level fair value coverage details."""
    if dr_exec_df is None or dr_exec_df.empty:
        return pd.DataFrame(columns=["DR_Ticker", "UnderlyingTicker", "HasFairValueInput", "FairValueSupported", "warnings"])
        
    cols = ["DR_Ticker", "UnderlyingTicker", "HasFairValueInput", "FairValueSupported", "warnings"]
    existing_cols = [c for c in cols if c in dr_exec_df.columns]
    return dr_exec_df[existing_cols].copy()


def summarize_dr_tracking_coverage(dr_exec_df: pd.DataFrame | None) -> pd.DataFrame:
    """Return ticker-level tracking and correlation coverage details."""
    if dr_exec_df is None or dr_exec_df.empty:
        return pd.DataFrame(columns=["DR_Ticker", "UnderlyingTicker", "TrackingSupported", "tracking_correlation", "tracking_error", "warnings"])
        
    cols = ["DR_Ticker", "UnderlyingTicker", "TrackingSupported", "tracking_correlation", "tracking_error", "warnings"]
    existing_cols = [c for c in cols if c in dr_exec_df.columns]
    return dr_exec_df[existing_cols].copy()
