from __future__ import annotations

import pandas as pd


def _join_mapping(flow_df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    if "Ticker" not in flow_df.columns or "Ticker" not in mapping_df.columns:
        raise ValueError("flow_df and mapping_df must include Ticker")
    return flow_df.merge(mapping_df, on="Ticker", how="left")


def aggregate_flow_by_asset_class(flow_df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate ticker flow proxy scores by asset class."""
    merged = _join_mapping(flow_df, mapping_df)
    return aggregate_flow_by_group(merged, "asset_class")


def aggregate_flow_by_group(flow_df: pd.DataFrame, group_column: str = "group") -> pd.DataFrame:
    """Aggregate ticker flow proxy scores by a configured group."""
    if group_column not in flow_df.columns:
        raise ValueError(f"Missing group column: {group_column}")
    grouped = (
        flow_df.dropna(subset=[group_column])
        .groupby(group_column, dropna=True)
        .agg(flow_score=("flow_score", "mean"), instrument_count=("Ticker", "nunique"))
        .reset_index()
        .sort_values("flow_score", ascending=False)
    )
    return grouped


def aggregate_flow_by_subgroup(flow_df: pd.DataFrame, subgroup_column: str = "subgroup") -> pd.DataFrame:
    """Aggregate ticker flow proxy scores by a configured subgroup."""
    return aggregate_flow_by_group(flow_df, subgroup_column)


def rank_top_inflows(flow_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Rank strongest ticker-level or group-level flow proxy scores."""
    return flow_df.sort_values("flow_score", ascending=False).head(n).reset_index(drop=True)


def rank_top_outflows(flow_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Rank weakest ticker-level or group-level flow proxy scores."""
    return flow_df.sort_values("flow_score", ascending=True).head(n).reset_index(drop=True)
