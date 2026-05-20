import numpy as np
import pandas as pd

from src.data_loader import get_price_column, pivot_prices
from src.returns import log_returns, simple_returns


def test_pivot_prices_prefers_adjusted_close():
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01", "2026-01-01"]),
            "Ticker": ["AAA", "BBB"],
            "Open": [10, 20],
            "High": [10, 20],
            "Low": [10, 20],
            "Close": [10, 20],
            "Adjusted Close": [9, 19],
            "Volume": [100, 200],
        }
    )

    assert get_price_column(df) == "Adjusted Close"
    prices = pivot_prices(df)
    assert prices.loc[pd.Timestamp("2026-01-01"), "AAA"] == 9


def test_simple_and_log_returns():
    prices = pd.DataFrame({"AAA": [100.0, 110.0, 121.0]}, index=pd.date_range("2026-01-01", periods=3))

    simple = simple_returns(prices)
    logs = log_returns(prices)

    assert np.isclose(simple["AAA"].iloc[1], 0.10)
    assert np.isclose(logs["AAA"].iloc[1], np.log(1.10))
