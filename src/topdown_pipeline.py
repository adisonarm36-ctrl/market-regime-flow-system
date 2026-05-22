from __future__ import annotations

import pandas as pd

from .asset_rotation import aggregate_flow_by_asset_class
from .clustering import calculate_cluster_breadth, calculate_cluster_momentum, cluster_membership_table, hierarchical_clustering, rank_clusters
from .correlation import static_correlation_matrix
from .country_breadth import calculate_country_breadth
from .dr_quality import build_dr_quality_table, rank_dr_candidates
from .global_flow import build_flow_table
from .momentum import calculate_momentum_table
from .redundancy import redundancy_report
from .returns import simple_returns
from .sector_breadth import aggregate_breadth_by_sector
from .stock_selection import build_research_candidates
from .thailand_breadth import calculate_thai_market_breadth
from .config_loader import load_yaml
from .data_adapters import get_data_adapter
from .data_quality import summarize_layer_availability, summarize_reference_data_quality, summarize_ticker_metadata_coverage
from .data_loader import pivot_prices, pivot_volume
from .reference_data import load_asset_map, load_country_map, load_dr_mapping, load_metadata, load_sector_map, merge_reference_data


def run_topdown_pipeline(
    price_df: pd.DataFrame,
    volume_df: pd.DataFrame | None = None,
    metadata_df: pd.DataFrame | None = None,
    asset_mapping_df: pd.DataFrame | None = None,
    country_map_df: pd.DataFrame | None = None,
    thailand_metadata_df: pd.DataFrame | None = None,
    dr_mapping_df: pd.DataFrame | None = None,
    dr_price_df: pd.DataFrame | None = None,
    dr_volume_df: pd.DataFrame | None = None,
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
        outputs.update(calculate_thai_market_breadth(price_df, thailand_metadata_df))
    else:
        outputs["thailand_market_health"] = pd.DataFrame()

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

    if dr_mapping_df is not None and dr_price_df is not None and dr_volume_df is not None:
        dr_quality = build_dr_quality_table(
            dr_price_df=dr_price_df,
            dr_volume_df=dr_volume_df,
            mapping_df=dr_mapping_df,
            underlying_price_df=price_df,
        )
        outputs["dr_quality_ranking"] = rank_dr_candidates(dr_quality)
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

    if metadata is not None and not metadata.empty:
        metadata, merge_warnings = merge_reference_data(price_df, metadata, sector_map, country_map)
        warnings.extend(merge_warnings)
    else:
        warnings.append("metadata missing; country, Thailand, sector, and stock ranking layers may be skipped")

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
        dr_mapping_df=dr_mapping,
        dr_price_df=dr_price_df,
        dr_volume_df=dr_volume_df,
    )
    outputs["warnings"] = pd.DataFrame({"warning": warnings})
    outputs["data_quality_report"] = summarize_reference_data_quality(price_df, metadata, dr_mapping)
    outputs["reference_data_report"] = summarize_ticker_metadata_coverage(price_df, metadata)
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


def _normalize_metadata(metadata_df: pd.DataFrame | None) -> pd.DataFrame | None:
    if metadata_df is None:
        return None
    result = metadata_df.copy()
    if "Suspended" in result.columns:
        result["Suspended"] = result["Suspended"].map(lambda value: str(value).lower() == "true" if pd.notna(value) else False)
    return result
