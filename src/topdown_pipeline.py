from __future__ import annotations

import pandas as pd

from .asset_rotation import aggregate_flow_by_asset_class
from .clustering import calculate_cluster_breadth, calculate_cluster_momentum, cluster_membership_table, hierarchical_clustering, rank_clusters
from .correlation import static_correlation_matrix
from .country_breadth import calculate_country_breadth
from .dr_mapping import identify_duplicate_dr_underlyings, normalize_dr_mapping
from .dr_quality import (
    build_dr_quality_table,
    rank_dr_candidates,
    rank_dr_candidates_by_reference_quality,
    rank_dr_candidates_with_execution_quality,
)
from .dr_valuation import (
    load_dr_market_data,
    load_dr_bid_ask_data,
    load_dr_fair_value_inputs,
    load_fx_rates,
    load_underlying_prices,
)
from .global_flow import build_flow_table
from .momentum import calculate_momentum_table
from .redundancy import redundancy_report
from .returns import simple_returns
from .sector_breadth import aggregate_breadth_by_sector
from .stock_selection import build_research_candidates
from .thailand_breadth import calculate_thai_market_breadth, filter_thailand_domestic_breadth_universe
from .config_loader import load_yaml
from .data_adapters import get_data_adapter
from .data_quality import (
    summarize_layer_availability,
    summarize_reference_data_quality,
    summarize_thailand_breadth_eligibility,
    summarize_thailand_dr_mapping_quality,
    summarize_thailand_reference_quality,
    summarize_ticker_metadata_coverage,
    summarize_dr_execution_quality_data,
    summarize_dr_fair_value_coverage,
    summarize_dr_tracking_coverage,
)
from .data_loader import pivot_prices, pivot_volume
from .reference_data import load_asset_map, load_country_map, load_dr_mapping, load_metadata, load_sector_map, merge_reference_data
from .thailand_reference import (
    load_thailand_dr_mapping,
    load_thailand_liquidity,
    load_thailand_sector_map,
    load_thailand_security_types,
    load_thailand_universe,
)


def run_topdown_pipeline(
    price_df: pd.DataFrame,
    volume_df: pd.DataFrame | None = None,
    metadata_df: pd.DataFrame | None = None,
    asset_mapping_df: pd.DataFrame | None = None,
    country_map_df: pd.DataFrame | None = None,
    thailand_metadata_df: pd.DataFrame | None = None,
    thailand_liquidity_df: pd.DataFrame | None = None,
    thailand_universe: str = "SET ex-DR",
    thailand_min_avg_value_20d: float | None = None,
    thailand_min_trading_days_ratio_60d: float | None = None,
    dr_mapping_df: pd.DataFrame | None = None,
    dr_price_df: pd.DataFrame | None = None,
    dr_volume_df: pd.DataFrame | None = None,
    dr_market_data_df: pd.DataFrame | None = None,
    dr_bid_ask_df: pd.DataFrame | None = None,
    fair_value_inputs_df: pd.DataFrame | None = None,
    underlying_prices_df: pd.DataFrame | None = None,
    fx_rates_df: pd.DataFrame | None = None,
    benchmark_ticker: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Run report-ready top-down research outputs from supplied CSV-derived data."""
    outputs: dict[str, pd.DataFrame] = {}
    metadata_df = _normalize_metadata(metadata_df)
    if country_map_df is None and metadata_df is not None and {"Ticker", "Country"}.issubset(metadata_df.columns):
        country_map_df = metadata_df[["Ticker", "Country"]].dropna().drop_duplicates()
    if thailand_metadata_df is None and metadata_df is not None and "Country" in metadata_df.columns:
        thailand_metadata_df = metadata_df[metadata_df["Country"].eq("Thailand")].copy()

    flow = build_flow_table(price_df, volume_df=volume_df, benchmark_ticker=benchmark_ticker)
    outputs["global_flow_summary"] = flow
    if asset_mapping_df is not None and not asset_mapping_df.empty:
        outputs["asset_class_flow_summary"] = aggregate_flow_by_asset_class(flow, asset_mapping_df)

    if country_map_df is not None and not country_map_df.empty:
        outputs["country_breadth_summary"] = calculate_country_breadth(price_df, country_map_df)
    else:
        outputs["country_breadth_summary"] = pd.DataFrame()

    if thailand_metadata_df is not None and not thailand_metadata_df.empty:
        outputs.update(
            calculate_thai_market_breadth(
                price_df,
                thailand_metadata_df,
                universe=thailand_universe,
                min_average_traded_value_20d=thailand_min_avg_value_20d or 0,
                liquidity_df=thailand_liquidity_df,
                min_trading_days_ratio_60d=thailand_min_trading_days_ratio_60d,
            )
        )
        outputs["thailand_excluded_securities"] = outputs.get("excluded_securities", pd.DataFrame())
    else:
        outputs["thailand_market_health"] = pd.DataFrame()
        outputs["thailand_excluded_securities"] = pd.DataFrame()

    if metadata_df is not None and not metadata_df.empty and {"Ticker", "Sector"}.issubset(metadata_df.columns):
        outputs["sector_breadth_summary"] = aggregate_breadth_by_sector(price_df, metadata_df)
    else:
        outputs["sector_breadth_summary"] = pd.DataFrame()

    returns = simple_returns(price_df).dropna(how="all")
    corr = static_correlation_matrix(returns) if not returns.empty else pd.DataFrame()
    outputs["correlation_matrix"] = corr
    if not corr.empty:
        labels = hierarchical_clustering(corr)
        membership = cluster_membership_table(labels)
        cluster_momentum = calculate_cluster_momentum(price_df, labels)
        cluster_breadth = calculate_cluster_breadth(price_df, labels)
        outputs["cluster_membership"] = membership
        outputs["cluster_summary"] = rank_clusters(cluster_momentum, cluster_breadth)
    else:
        outputs["cluster_membership"] = pd.DataFrame()
        outputs["cluster_summary"] = pd.DataFrame()

    momentum = calculate_momentum_table(price_df)
    outputs["momentum_summary"] = momentum

    outputs["redundancy_report"] = redundancy_report(corr, momentum) if not corr.empty else pd.DataFrame()

    # Setup five default empty reports
    outputs["dr_execution_quality_report"] = pd.DataFrame(columns=[
        "DR_Ticker", "UnderlyingTicker", "IsActive", "LiquiditySupported", "SpreadSupported",
        "FairValueSupported", "TrackingSupported", "confidence_level", "quality_label", "quality_score"
    ])
    outputs["dr_fair_value_report"] = pd.DataFrame(columns=[
        "DR_Ticker", "UnderlyingTicker", "fair_value", "premium_discount_pct"
    ])
    outputs["dr_tracking_report"] = pd.DataFrame(columns=[
        "DR_Ticker", "UnderlyingTicker", "tracking_correlation", "tracking_error"
    ])
    outputs["dr_liquidity_report"] = pd.DataFrame(columns=[
        "DR_Ticker", "UnderlyingTicker", "average_traded_value_20d", "volume_consistency"
    ])
    outputs["dr_quality_warnings"] = pd.DataFrame(columns=[
        "DR_Ticker", "warnings"
    ])

    if dr_mapping_df is not None and not dr_mapping_df.empty:
        dr_mapping_df = normalize_dr_mapping(dr_mapping_df)
        
        # If dr_market_data_df is None, but dr_price_df is provided:
        if dr_market_data_df is None and dr_price_df is not None and not dr_price_df.empty:
            long_prices = dr_price_df.reset_index().melt(id_vars=["Date"], var_name="DR_Ticker", value_name="Close")
            if dr_volume_df is not None and not dr_volume_df.empty:
                long_volumes = dr_volume_df.reset_index().melt(id_vars=["Date"], var_name="DR_Ticker", value_name="Volume")
                dr_market_data_df = pd.merge(long_prices, long_volumes, on=["Date", "DR_Ticker"], how="left")
            else:
                dr_market_data_df = long_prices
                dr_market_data_df["Volume"] = 0
            dr_market_data_df["Open"] = dr_market_data_df["Close"]
            dr_market_data_df["High"] = dr_market_data_df["Close"]
            dr_market_data_df["Low"] = dr_market_data_df["Close"]
            dr_market_data_df["ValueTraded"] = dr_market_data_df["Close"] * dr_market_data_df["Volume"]
            
        # Check if we have core DR price time series to perform full execution quality ranking.
        # If we don't have transaction/price data in the current dataset (dr_price_df is None or empty), we fall back to reference-only!
        if dr_price_df is None or dr_price_df.empty:
            outputs["dr_quality_ranking"] = rank_dr_candidates_by_reference_quality(dr_mapping_df)
            outputs["dr_execution_quality_report"] = outputs["dr_quality_ranking"]
        else:
            try:
                quality_res = rank_dr_candidates_with_execution_quality(
                    dr_mapping_df=dr_mapping_df,
                    dr_market_data_df=dr_market_data_df,
                    dr_bid_ask_df=dr_bid_ask_df,
                    fair_value_inputs_df=fair_value_inputs_df,
                    underlying_prices_df=underlying_prices_df,
                    fx_rates_df=fx_rates_df
                )
                outputs["dr_execution_quality_report"] = quality_res
                outputs["dr_quality_ranking"] = quality_res
                
                if not quality_res.empty:
                    fv_cols = [c for c in ["DR_Ticker", "UnderlyingTicker", "fair_value", "premium_discount_pct"] if c in quality_res.columns]
                    outputs["dr_fair_value_report"] = quality_res[fv_cols].dropna(subset=[c for c in ["fair_value", "premium_discount_pct"] if c in fv_cols], how="all").reset_index(drop=True)
                    
                    track_cols = [c for c in ["DR_Ticker", "UnderlyingTicker", "tracking_correlation", "tracking_error"] if c in quality_res.columns]
                    outputs["dr_tracking_report"] = quality_res[track_cols].dropna(subset=[c for c in ["tracking_correlation", "tracking_error"] if c in track_cols], how="all").reset_index(drop=True)
                    
                    liq_cols = [c for c in ["DR_Ticker", "UnderlyingTicker", "average_traded_value_20d", "volume_consistency"] if c in quality_res.columns]
                    outputs["dr_liquidity_report"] = quality_res[liq_cols].dropna(subset=[c for c in ["average_traded_value_20d", "volume_consistency"] if c in liq_cols], how="all").reset_index(drop=True)
                    
                    warn_cols = [c for c in ["DR_Ticker", "warnings"] if c in quality_res.columns]
                    outputs["dr_quality_warnings"] = quality_res[warn_cols].copy()
            except Exception as e:
                outputs["dr_quality_ranking"] = rank_dr_candidates_by_reference_quality(dr_mapping_df)
    else:
        missing = []
        if dr_mapping_df is None:
            missing.append("dr_mapping")
        if dr_price_df is None:
            missing.append("dr_prices")
        if dr_volume_df is None:
            missing.append("dr_volume")
        outputs["dr_quality_ranking"] = pd.DataFrame(
            [{"data_quality_warning": f"DR quality skipped: missing optional data ({', '.join(missing)})"}]
        )

    if metadata_df is not None and not metadata_df.empty:
        cluster_for_selection = outputs["cluster_membership"].merge(outputs["cluster_summary"], on="cluster", how="left") if not outputs["cluster_membership"].empty else None
        outputs["stock_ranking"] = build_research_candidates(
            metadata_df=metadata_df,
            momentum_df=momentum,
            country_regime_df=outputs["country_breadth_summary"],
            sector_breadth_df=outputs["sector_breadth_summary"],
            cluster_summary_df=cluster_for_selection,
            redundancy_report_df=outputs["redundancy_report"],
            dr_quality_df=outputs["dr_quality_ranking"],
        )
    else:
        outputs["stock_ranking"] = pd.DataFrame()

    return outputs


def run_pipeline_from_config(config_path: str = "config/data_sources.yaml", adapter=None) -> dict[str, pd.DataFrame]:
    """Run the top-down pipeline from configured data source and local reference data."""
    config = load_yaml(config_path)
    adapter = adapter or get_data_adapter(config)
    warnings: list[str] = []
    prices_long = adapter.load_prices()
    warnings.extend(getattr(adapter, "warnings", []))
    price_df = pivot_prices(prices_long)
    volume_df = pivot_volume(prices_long)

    metadata = _load_reference_from_adapter_or_config(adapter, config, "metadata_path", load_metadata, warnings)
    sector_map = _load_reference_from_adapter_or_config(adapter, config, "sector_map_path", load_sector_map, warnings)
    country_map = _load_reference_from_adapter_or_config(adapter, config, "country_map_path", load_country_map, warnings)
    asset_map = _load_reference_from_adapter_or_config(adapter, config, "asset_map_path", load_asset_map, warnings)
    dr_mapping = _load_reference_from_adapter_or_config(adapter, config, "dr_mapping_path", load_dr_mapping, warnings)
    thailand_universe_df = _load_reference_from_config(config, "thailand_universe_path", load_thailand_universe, warnings)
    thailand_sector_map = _load_reference_from_config(config, "thailand_sector_map_path", load_thailand_sector_map, warnings)
    thailand_security_types = _load_reference_from_config(config, "thailand_security_types_path", load_thailand_security_types, warnings)
    thailand_liquidity = _load_reference_from_config(config, "thailand_liquidity_path", load_thailand_liquidity, warnings)
    thailand_dr_mapping = _load_reference_from_config(config, "thailand_dr_mapping_path", load_thailand_dr_mapping, warnings)

    # Phase 5A: Load enhanced DR execution quality dataframes
    dr_market_data = _load_reference_from_config(config, "dr_market_data_path", load_dr_market_data, warnings)
    dr_bid_ask = _load_reference_from_config(config, "dr_bid_ask_path", load_dr_bid_ask_data, warnings)
    dr_fair_value_inputs = _load_reference_from_config(config, "dr_fair_value_inputs_path", load_dr_fair_value_inputs, warnings)
    fx_rates = _load_reference_from_config(config, "fx_rates_path", load_fx_rates, warnings)
    underlying_prices = _load_reference_from_config(config, "underlying_prices_path", load_underlying_prices, warnings)

    if thailand_dr_mapping is not None and not thailand_dr_mapping.empty:
        dr_mapping = normalize_dr_mapping(thailand_dr_mapping)

    if metadata is not None and not metadata.empty:
        metadata, merge_warnings = merge_reference_data(price_df, metadata, sector_map, country_map)
        warnings.extend(merge_warnings)
    else:
        warnings.append("metadata missing; country, Thailand, sector, and stock ranking layers may be skipped")

    thailand_config = _load_thailand_universe_config(warnings)
    selected_thailand_universe = thailand_config.get("default_universe", "SET100")
    liquidity_filter = thailand_config.get("liquidity_filter", {})
    min_avg_value = liquidity_filter.get("min_avg_value_20d_thb")
    min_trading_ratio = liquidity_filter.get("min_trading_days_ratio_60d")

    thailand_metadata = thailand_universe_df
    if thailand_metadata is None or thailand_metadata.empty:
        thailand_metadata = metadata[metadata["Country"].eq("Thailand")].copy() if metadata is not None and "Country" in metadata.columns else None

    thailand_eligibility = None
    if thailand_metadata is not None and not thailand_metadata.empty:
        try:
            thailand_eligibility = filter_thailand_domestic_breadth_universe(
                thailand_metadata,
                liquidity_df=thailand_liquidity,
                universe=selected_thailand_universe,
                min_avg_value_20d=min_avg_value,
                min_trading_days_ratio_60d=min_trading_ratio,
            )
        except Exception as exc:
            warnings.append(f"Thailand eligibility skipped: {exc}")

    dr_price_df = dr_volume_df = None
    if dr_mapping is not None and not dr_mapping.empty and "DR_Ticker" in dr_mapping.columns:
        dr_tickers = [ticker for ticker in dr_mapping["DR_Ticker"] if ticker in price_df.columns]
        if dr_tickers:
            dr_price_df = price_df[dr_tickers]
            dr_volume_df = volume_df[dr_tickers]
        else:
            warnings.append("DR mapping exists but no DR tickers are present in price data")

    outputs = run_topdown_pipeline(
        price_df=price_df,
        volume_df=volume_df,
        metadata_df=metadata,
        asset_mapping_df=asset_map,
        country_map_df=country_map,
        thailand_metadata_df=thailand_metadata,
        thailand_liquidity_df=thailand_liquidity,
        thailand_universe=selected_thailand_universe,
        thailand_min_avg_value_20d=min_avg_value,
        thailand_min_trading_days_ratio_60d=min_trading_ratio,
        dr_mapping_df=dr_mapping,
        dr_price_df=dr_price_df,
        dr_volume_df=dr_volume_df,
        dr_market_data_df=dr_market_data,
        dr_bid_ask_df=dr_bid_ask,
        fair_value_inputs_df=dr_fair_value_inputs,
        underlying_prices_df=underlying_prices,
        fx_rates_df=fx_rates,
    )
    outputs["warnings"] = pd.DataFrame({"warning": warnings})
    outputs["data_quality_report"] = summarize_reference_data_quality(price_df, metadata, dr_mapping)
    outputs["reference_data_report"] = summarize_ticker_metadata_coverage(price_df, metadata)
    outputs["thailand_reference_report"] = summarize_thailand_reference_quality(
        thailand_universe_df,
        thailand_sector_map,
        thailand_security_types,
        thailand_liquidity,
        thailand_dr_mapping,
    )
    outputs["thailand_eligibility_report"] = summarize_thailand_breadth_eligibility(thailand_eligibility)
    outputs["thailand_dr_mapping_report"] = summarize_thailand_dr_mapping_quality(thailand_dr_mapping if thailand_dr_mapping is not None else dr_mapping)
    outputs["dr_duplicate_underlying_report"] = identify_duplicate_dr_underlyings(dr_mapping) if dr_mapping is not None and not dr_mapping.empty else pd.DataFrame()
    outputs["dr_execution_quality_data_report"] = summarize_dr_execution_quality_data(dr_market_data, dr_bid_ask)
    outputs["dr_fair_value_coverage_report"] = summarize_dr_fair_value_coverage(dr_fair_value_inputs, underlying_prices, fx_rates)
    outputs["dr_tracking_coverage_report"] = summarize_dr_tracking_coverage(dr_market_data, underlying_prices, fx_rates)
    outputs["pipeline_layer_status"] = summarize_layer_availability(outputs, warnings)
    return outputs


def _load_reference_from_adapter_or_config(adapter, config: dict, key: str, loader, warnings: list[str]) -> pd.DataFrame | None:
    active = config.get("active_source", "csv")
    reference = config.get("source_settings", {}).get(active, {}).get("reference_data", {})
    path = reference.get(key)
    if path:
        try:
            return loader(path)
        except Exception as exc:
            warnings.append(f"{key} skipped: {exc}")
    try:
        if key == "metadata_path":
            return adapter.load_metadata()
        if key == "sector_map_path":
            return adapter.load_sector_map()
        if key == "dr_mapping_path":
            return adapter.load_dr_mapping()
    except Exception as exc:
        warnings.append(f"{key} skipped: {exc}")
        return None
    warnings.append(f"{key} missing")
    return None


def _load_reference_from_config(config: dict, key: str, loader, warnings: list[str]) -> pd.DataFrame | None:
    active = config.get("active_source", "csv")
    active_settings = config.get("source_settings", {}).get(active, {})
    path = active_settings.get("reference_data", {}).get(key)
    if not path:
        for settings in config.get("source_settings", {}).values():
            path = settings.get("reference_data", {}).get(key)
            if path:
                break
    if not path:
        warnings.append(f"{key} missing")
        return None
    try:
        df = loader(path)
        for warning in getattr(df, "attrs", {}).get("warnings", []):
            warnings.append(f"{key}: {warning}")
        return df
    except Exception as exc:
        warnings.append(f"{key} skipped: {exc}")
        return None


def _load_thailand_universe_config(warnings: list[str]) -> dict:
    try:
        config = load_yaml("config/thailand_universe.yaml")
    except Exception as exc:
        warnings.append(f"thailand_universe.yaml skipped: {exc}")
        return {"default_universe": "SET100", "liquidity_filter": {}}
    if config.get("default_universe") == "SET_ex_DR":
        config["default_universe"] = "SET ex-DR"
    return config


def _normalize_metadata(metadata_df: pd.DataFrame | None) -> pd.DataFrame | None:
    if metadata_df is None:
        return None
    result = metadata_df.copy()
    if "Suspended" in result.columns:
        result["Suspended"] = result["Suspended"].map(lambda value: str(value).lower() == "true" if pd.notna(value) else False)
    return result
