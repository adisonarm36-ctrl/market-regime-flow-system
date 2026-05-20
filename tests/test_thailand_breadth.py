import pandas as pd

from src.thailand_breadth import (
    calculate_thai_market_breadth,
    excluded_securities_summary,
    filter_thailand_domestic_universe,
)


def test_filter_thailand_domestic_universe_excludes_dr_and_illiquid():
    metadata = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB", "CCC", "DDD"],
            "SecurityType": ["Stock", "DR", "Stock", "ETF"],
            "Universe": ["SET ex-DR", "SET ex-DR", "SET ex-DR", "SET ex-DR"],
            "Suspended": [False, False, False, False],
            "average_traded_value_20d": [100, 100, 0, 100],
        }
    )

    included, excluded = filter_thailand_domestic_universe(metadata, "SET ex-DR", min_average_traded_value_20d=50)
    summary = excluded_securities_summary(excluded)

    assert included["Ticker"].tolist() == ["AAA"]
    assert "BBB" in excluded["Ticker"].tolist()
    assert "CCC" in excluded["Ticker"].tolist()
    assert set(summary["exclusion_reason"]) >= {"excluded_security_type", "illiquid"}


def test_calculate_thai_market_breadth_never_mixes_drs():
    dates = pd.date_range("2026-01-01", periods=260)
    prices = pd.DataFrame(
        {
            "AAA": range(100, 360),
            "DR1": range(200, 460),
        },
        index=dates,
        dtype=float,
    )
    metadata = pd.DataFrame(
        {
            "Ticker": ["AAA", "DR1"],
            "SecurityType": ["Stock", "DR"],
            "Universe": ["SET ex-DR", "SET ex-DR"],
            "Suspended": [False, False],
            "average_traded_value_20d": [100, 100],
        }
    )

    result = calculate_thai_market_breadth(prices, metadata, universe="SET ex-DR")

    assert result["included_securities"]["Ticker"].tolist() == ["AAA"]
    assert result["thailand_market_health"]["instrument_count"].iloc[0] == 1
