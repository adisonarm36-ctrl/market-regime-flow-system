import pandas as pd

from src.redundancy import (
    detect_high_correlation_pairs,
    detect_redundant_instruments_inside_cluster,
    redundancy_report,
    select_preferred_instrument,
)


def test_detect_high_correlation_pairs():
    corr = pd.DataFrame(
        {
            "AAA": [1.0, 0.9, 0.2],
            "BBB": [0.9, 1.0, 0.1],
            "CCC": [0.2, 0.1, 1.0],
        },
        index=["AAA", "BBB", "CCC"],
    )

    pairs = detect_high_correlation_pairs(corr, threshold=0.85)

    assert len(pairs) == 1
    assert pairs.iloc[0]["Ticker_A"] == "AAA"
    assert pairs.iloc[0]["Ticker_B"] == "BBB"


def test_select_preferred_instrument_and_report():
    corr = pd.DataFrame({"AAA": [1.0, 0.92], "BBB": [0.92, 1.0]}, index=["AAA", "BBB"])
    metrics = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB"],
            "momentum_score": [80, 70],
            "liquidity": [1000, 2000],
            "spread_bps": [10, 5],
            "trend_quality": [2, 2],
        }
    )

    preferred = select_preferred_instrument(metrics)
    report = redundancy_report(corr, metrics, threshold=0.85)

    assert preferred["Ticker"] == "AAA"
    assert report["preferred_ticker"].iloc[0] == "AAA"
    assert report["redundant_ticker"].iloc[0] == "BBB"


def test_detect_redundant_instruments_inside_cluster():
    corr = pd.DataFrame({"AAA": [1.0, 0.91], "BBB": [0.91, 1.0]}, index=["AAA", "BBB"])
    labels = pd.Series({"AAA": 3, "BBB": 3})

    result = detect_redundant_instruments_inside_cluster(labels, corr, threshold=0.85)

    assert result["cluster"].iloc[0] == 3
