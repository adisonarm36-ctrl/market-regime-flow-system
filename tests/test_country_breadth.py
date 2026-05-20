import pandas as pd

from src.country_breadth import (
    calculate_breadth_timeseries,
    calculate_country_breadth,
    distance_from_52week_high,
    rolling_52week_high,
)


def test_52week_high_and_distance_from_high():
    prices = pd.DataFrame({"AAA": [10.0, 12.0, 11.0]}, index=pd.date_range("2026-01-01", periods=3))

    high = rolling_52week_high(prices)
    distance = distance_from_52week_high(prices)

    assert high["AAA"].iloc[-1] == 12.0
    assert round(distance["AAA"].iloc[-1], 4) == round(11.0 / 12.0 - 1.0, 4)


def test_country_breadth_buckets_and_regime():
    dates = pd.date_range("2026-01-01", periods=260)
    prices = pd.DataFrame(
        {
            "AAA": range(100, 360),
            "BBB": range(200, 460),
            "CCC": [100] * 259 + [70],
        },
        index=dates,
        dtype=float,
    )

    breadth = calculate_breadth_timeseries(prices)
    latest = breadth.iloc[-1]

    assert latest["pct_within_5pct_high"] > 60
    assert latest["pct_down_more_20pct"] > 0
    assert latest["regime"] in {"Strong Bull", "Bull", "Neutral", "Bear Warning", "Bear"}


def test_calculate_country_breadth_reports_missing_data():
    prices = pd.DataFrame({"AAA": [1, 2, 3]}, index=pd.date_range("2026-01-01", periods=3))
    country_map = pd.DataFrame({"Ticker": ["ZZZ"], "Country": ["Nowhere"]})

    summary = calculate_country_breadth(prices, country_map)

    assert summary["missing_data"].iloc[0] == "No configured tickers found in price data"
