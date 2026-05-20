import pandas as pd

from src.sector_breadth import (
    aggregate_breadth_by_industry,
    aggregate_breadth_by_sector,
    calculate_group_breadth_timeseries,
    detect_deteriorating_sectors,
    detect_improving_sectors,
    rank_strongest_sectors,
    rank_weakest_sectors,
)


def _prices():
    dates = pd.date_range("2026-01-01", periods=260)
    return pd.DataFrame(
        {
            "AAA": range(100, 360),
            "BBB": range(90, 350),
            "CCC": range(360, 100, -1),
            "DDD": [100] * 260,
        },
        index=dates,
        dtype=float,
    )


def _metadata():
    return pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB", "CCC", "DDD"],
            "Country": ["Thailand", "Thailand", "Thailand", "United States"],
            "Sector": ["Technology", "Technology", "Energy", "Utilities"],
            "Industry": ["Software", "Hardware", "Oil", "Power"],
        }
    )


def test_aggregate_breadth_by_sector_and_industry():
    sector = aggregate_breadth_by_sector(_prices(), _metadata(), country="Thailand")
    industry = aggregate_breadth_by_industry(_prices(), _metadata(), country="Thailand")

    assert set(sector["Sector"]) == {"Technology", "Energy"}
    assert set(industry["Industry"]) == {"Software", "Hardware", "Oil"}
    assert rank_strongest_sectors(sector, 1)["Sector"].iloc[0] == "Technology"
    assert rank_weakest_sectors(sector, 1)["Sector"].iloc[0] == "Energy"


def test_detect_improving_and_deteriorating_sectors():
    timeseries = calculate_group_breadth_timeseries(_prices(), _metadata(), "Sector")

    improving = detect_improving_sectors(timeseries, "Sector", lookback=20)
    deteriorating = detect_deteriorating_sectors(timeseries, "Sector", lookback=20)

    assert "score_change" in improving.columns
    assert improving.iloc[0]["score_change"] >= improving.iloc[-1]["score_change"]
    assert deteriorating.iloc[0]["score_change"] <= deteriorating.iloc[-1]["score_change"]
