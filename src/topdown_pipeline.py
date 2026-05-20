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
        outputs["dr_quality_ranking"] = pd.DataFrame()

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
