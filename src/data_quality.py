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


def summarize_dr_execution_quality_data(
    dr_market_data: pd.DataFrame | None,
    dr_bid_ask: pd.DataFrame | None
) -> pd.DataFrame:
    """Summarize local DR execution quality market and spread data counts and status."""
    import numpy as np
    market_rows = len(dr_market_data) if dr_market_data is not None else 0
    bid_ask_rows = len(dr_bid_ask) if dr_bid_ask is not None else 0
    
    unique_market_tickers = 0
    if dr_market_data is not None and "DR_Ticker" in dr_market_data.columns:
        unique_market_tickers = int(dr_market_data["DR_Ticker"].nunique())
        
    unique_bid_ask_tickers = 0
    if dr_bid_ask is not None and "DR_Ticker" in dr_bid_ask.columns:
        unique_bid_ask_tickers = int(dr_bid_ask["DR_Ticker"].nunique())
        
    avg_spread_pct = np.nan
    if dr_bid_ask is not None and not dr_bid_ask.empty:
        if "Bid" in dr_bid_ask.columns and "Ask" in dr_bid_ask.columns:
            bids = dr_bid_ask["Bid"]
            asks = dr_bid_ask["Ask"]
            mids = (bids + asks) / 2.0
            valid = (mids > 0)
            if valid.any():
                spreads = ((asks[valid] - bids[valid]) / mids[valid]) * 100.0
                avg_spread_pct = float(spreads.mean())

    warnings = []
    if market_rows == 0:
        warnings.append("missing_dr_market_data")
    if bid_ask_rows == 0:
        warnings.append("missing_dr_bid_ask_data")
        
    return pd.DataFrame([
        {
            "dr_market_rows": market_rows,
            "dr_bid_ask_rows": bid_ask_rows,
            "unique_market_tickers": unique_market_tickers,
            "unique_bid_ask_tickers": unique_bid_ask_tickers,
            "avg_spread_pct": avg_spread_pct,
            "warnings": ";".join(warnings)
        }
    ])


def summarize_dr_fair_value_coverage(
    fair_value_inputs: pd.DataFrame | None,
    underlying_prices: pd.DataFrame | None,
    fx_rates: pd.DataFrame | None
) -> pd.DataFrame:
    """Summarize DR fair value data coverage (underlying prices and FX rate alignment)."""
    fv_rows = len(fair_value_inputs) if fair_value_inputs is not None else 0
    und_rows = len(underlying_prices) if underlying_prices is not None else 0
    fx_rows = len(fx_rates) if fx_rates is not None else 0
    
    unique_fv_tickers = 0
    if fair_value_inputs is not None and "DR_Ticker" in fair_value_inputs.columns:
        unique_fv_tickers = int(fair_value_inputs["DR_Ticker"].nunique())
        
    covered_tickers = 0
    missing_unds = []
    missing_fxs = []
    
    if fair_value_inputs is not None and not fair_value_inputs.empty:
        und_tickers_avail = set(underlying_prices["UnderlyingTicker"].unique()) if underlying_prices is not None and "UnderlyingTicker" in underlying_prices.columns else set()
        fx_pairs_avail = set(fx_rates["FXPair"].unique()) if fx_rates is not None and "FXPair" in fx_rates.columns else set()
        
        for _, row in fair_value_inputs.iterrows():
            und_ticker = row.get("UnderlyingTicker")
            fx_pair = row.get("FXPair")
            
            has_und = und_ticker in und_tickers_avail
            has_fx = fx_pair in fx_pairs_avail
            
            if has_und and has_fx:
                covered_tickers += 1
            if not has_und and pd.notna(und_ticker):
                missing_unds.append(str(und_ticker))
            if not has_fx and pd.notna(fx_pair):
                missing_fxs.append(str(fx_pair))
                
    coverage_pct = (covered_tickers / unique_fv_tickers * 100.0) if unique_fv_tickers > 0 else 0.0
    
    warnings = []
    if fv_rows == 0:
        warnings.append("missing_fair_value_inputs")
    if und_rows == 0:
        warnings.append("missing_underlying_prices")
    if fx_rows == 0:
        warnings.append("missing_fx_rates")
        
    return pd.DataFrame([
        {
            "fair_value_input_rows": fv_rows,
            "unique_fair_value_tickers": unique_fv_tickers,
            "underlying_prices_rows": und_rows,
            "fx_rates_rows": fx_rows,
            "coverage_pct": coverage_pct,
            "missing_underlying_tickers": ",".join(sorted(set(missing_unds))),
            "missing_fx_pairs": ",".join(sorted(set(missing_fxs))),
            "warnings": ";".join(warnings)
        }
    ])


def summarize_dr_tracking_coverage(
    dr_market_data: pd.DataFrame | None,
    underlying_prices: pd.DataFrame | None,
    fx_rates: pd.DataFrame | None
) -> pd.DataFrame:
    """Summarize overlapping dates and status for historical tracking calculations."""
    dr_tickers = 0
    common_dates_count = 0
    warnings = []
    
    if dr_market_data is not None and not dr_market_data.empty and "DR_Ticker" in dr_market_data.columns:
        dr_tickers = int(dr_market_data["DR_Ticker"].nunique())
        
        # Calculate overlap of dates
        dr_dates = set(pd.to_datetime(dr_market_data["Date"]).dt.date.unique())
        und_dates = set(pd.to_datetime(underlying_prices["Date"]).dt.date.unique()) if underlying_prices is not None and "Date" in underlying_prices.columns else set()
        fx_dates = set(pd.to_datetime(fx_rates["Date"]).dt.date.unique()) if fx_rates is not None and "Date" in fx_rates.columns else set()
        
        common_dates = dr_dates.intersection(und_dates).intersection(fx_dates)
        common_dates_count = len(common_dates)
        
    if dr_tickers == 0:
        warnings.append("missing_dr_market_data")
    if underlying_prices is None or underlying_prices.empty:
        warnings.append("missing_underlying_prices")
    if fx_rates is None or fx_rates.empty:
        warnings.append("missing_fx_rates")
        
    status = "Missing"
    if dr_tickers > 0 and common_dates_count >= 10:
        status = "Good"
    elif dr_tickers > 0 and common_dates_count > 0:
        status = "Partial"
        
    return pd.DataFrame([
        {
            "dr_market_tickers": dr_tickers,
            "common_dates_count": common_dates_count,
            "tracking_coverage_status": status,
            "warnings": ";".join(warnings)
        }
    ])

