import pandas as pd

from src.asset_rotation import aggregate_flow_by_asset_class, rank_top_inflows, rank_top_outflows
from src.global_flow import build_flow_table, calculate_flow_score, classify_flow


def test_flow_score_and_classification():
    metrics = pd.DataFrame(
        {
            "return_1d": [0.01, -0.02, 0.03],
            "return_5d": [0.02, -0.01, 0.04],
            "volume_zscore": [0.5, -1.0, 1.0],
        },
        index=["AAA", "BBB", "CCC"],
    )

    scores = calculate_flow_score(metrics)

    assert scores["CCC"] > scores["BBB"]
    assert classify_flow(80) == "Strong Inflow"
    assert classify_flow(20) == "Strong Outflow"


def test_build_flow_table_and_asset_rotation():
    dates = pd.date_range("2026-01-01", periods=65)
    prices = pd.DataFrame({"AAA": range(100, 165), "BBB": range(165, 100, -1)}, index=dates, dtype=float)
    volume = pd.DataFrame({"AAA": [100] * 64 + [300], "BBB": [100] * 65}, index=dates, dtype=float)

    flow = build_flow_table(prices, volume_df=volume, benchmark_ticker="AAA")
    mapping = pd.DataFrame({"Ticker": ["AAA", "BBB"], "asset_class": ["Equity", "Bond"]})
    aggregated = aggregate_flow_by_asset_class(flow, mapping)

    assert set(flow["signal_type"]) == {"price-based flow proxy"}
    assert rank_top_inflows(flow, 1)["Ticker"].iloc[0] == "AAA"
    assert rank_top_outflows(flow, 1)["Ticker"].iloc[0] == "BBB"
    assert set(aggregated["asset_class"]) == {"Equity", "Bond"}
