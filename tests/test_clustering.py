import pandas as pd

from src.clustering import (
    calculate_cluster_breadth,
    calculate_cluster_momentum,
    cluster_membership_table,
    hierarchical_clustering,
    rank_clusters,
)


def test_hierarchical_clustering_and_membership_table():
    corr = pd.DataFrame(
        {
            "AAA": [1.0, 0.95, 0.1],
            "BBB": [0.95, 1.0, 0.2],
            "CCC": [0.1, 0.2, 1.0],
        },
        index=["AAA", "BBB", "CCC"],
    )

    labels = hierarchical_clustering(corr, distance_threshold=0.2)
    members = cluster_membership_table(labels)

    assert labels["AAA"] == labels["BBB"]
    assert labels["AAA"] != labels["CCC"]
    assert set(members.columns) == {"Ticker", "cluster"}


def test_cluster_momentum_breadth_and_ranking():
    dates = pd.date_range("2026-01-01", periods=260)
    prices = pd.DataFrame(
        {
            "AAA": range(100, 360),
            "BBB": range(90, 350),
            "CCC": range(360, 100, -1),
        },
        index=dates,
        dtype=float,
    )
    labels = pd.Series({"AAA": 1, "BBB": 1, "CCC": 2}, name="cluster")

    momentum = calculate_cluster_momentum(prices, labels, window=20)
    breadth = calculate_cluster_breadth(prices, labels)
    ranked = rank_clusters(momentum, breadth)

    assert ranked["cluster"].iloc[0] == 1
    assert "cluster_score" in ranked.columns
