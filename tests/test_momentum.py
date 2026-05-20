import pandas as pd

from src.momentum import calculate_momentum, calculate_momentum_table, moving_average_trend_filter, rank_momentum


def test_momentum_table_and_ranking():
    dates = pd.date_range("2026-01-01", periods=260)
    prices = pd.DataFrame(
        {
            "AAA": range(100, 360),
            "BBB": range(360, 100, -1),
        },
        index=dates,
        dtype=float,
    )

    table = calculate_momentum_table(prices)
    ranked = rank_momentum(table, 1)

    assert calculate_momentum(prices, 21)["AAA"] > 0
    assert ranked["Ticker"].iloc[0] == "AAA"
    assert {"momentum_1m", "momentum_3m", "momentum_6m", "momentum_12m", "momentum_score"}.issubset(table.columns)


def test_moving_average_trend_filter():
    dates = pd.date_range("2026-01-01", periods=220)
    prices = pd.DataFrame({"AAA": range(100, 320), "BBB": range(320, 100, -1)}, index=dates, dtype=float)

    trend = moving_average_trend_filter(prices)

    assert trend.loc[trend["Ticker"].eq("AAA"), "trend_quality"].iloc[0] == 2
    assert trend.loc[trend["Ticker"].eq("BBB"), "trend_quality"].iloc[0] == 0
