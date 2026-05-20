from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from .country_breadth import calculate_breadth_timeseries


def hierarchical_clustering(correlation_df: pd.DataFrame, distance_threshold: float = 0.5) -> pd.Series:
    """Cluster instruments using hierarchical clustering on correlation distance."""
    if correlation_df.empty:
        return pd.Series(dtype="int64", name="cluster")
    if len(correlation_df.columns) == 1:
        return pd.Series([1], index=correlation_df.columns, name="cluster")

    corr = correlation_df.loc[correlation_df.columns, correlation_df.columns].fillna(0)
    distance = (1 - corr).clip(lower=0, upper=2).to_numpy(copy=True)
    np.fill_diagonal(distance, 0)
    condensed = squareform(distance, checks=False)
    linked = linkage(condensed, method="average")
    labels = fcluster(linked, t=distance_threshold, criterion="distance")
    return pd.Series(labels, index=corr.columns, name="cluster")


def cluster_membership_table(cluster_labels: pd.Series) -> pd.DataFrame:
    """Return a cluster membership table from ticker-indexed labels."""
    return cluster_labels.rename_axis("Ticker").reset_index(name="cluster").sort_values(["cluster", "Ticker"]).reset_index(drop=True)


def calculate_cluster_momentum(price_df: pd.DataFrame, cluster_labels: pd.Series, window: int = 20) -> pd.DataFrame:
    """Calculate latest average cluster momentum."""
    returns = price_df.sort_index().pct_change(window).iloc[-1]
    rows = []
    for cluster_id, members in cluster_labels.groupby(cluster_labels):
        tickers = [ticker for ticker in members.index if ticker in returns.index]
        rows.append({"cluster": cluster_id, "cluster_momentum": returns[tickers].mean(), "member_count": len(tickers)})
    return pd.DataFrame(rows).sort_values("cluster_momentum", ascending=False).reset_index(drop=True)


def calculate_cluster_breadth(price_df: pd.DataFrame, cluster_labels: pd.Series) -> pd.DataFrame:
    """Calculate latest breadth score for each cluster."""
    rows = []
    for cluster_id, members in cluster_labels.groupby(cluster_labels):
        tickers = [ticker for ticker in members.index if ticker in price_df.columns]
        if not tickers:
            rows.append({"cluster": cluster_id, "missing_data": "No cluster members found in price data"})
            continue
        breadth = calculate_breadth_timeseries(price_df[tickers])
        rows.append(
            {
                "cluster": cluster_id,
                "cluster_breadth_score": breadth["breadth_score"].iloc[-1],
                "member_count": len(tickers),
            }
        )
    return pd.DataFrame(rows).sort_values("cluster_breadth_score", ascending=False).reset_index(drop=True)


def rank_clusters(cluster_momentum_df: pd.DataFrame, cluster_breadth_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rank clusters by momentum and, when available, breadth."""
    result = cluster_momentum_df.copy()
    if cluster_breadth_df is not None and not cluster_breadth_df.empty:
        result = result.merge(cluster_breadth_df[["cluster", "cluster_breadth_score"]], on="cluster", how="left")
        result["cluster_score"] = result[["cluster_momentum", "cluster_breadth_score"]].rank(pct=True).mean(axis=1) * 100
    else:
        result["cluster_score"] = result["cluster_momentum"].rank(pct=True) * 100
    return result.sort_values("cluster_score", ascending=False).reset_index(drop=True)
