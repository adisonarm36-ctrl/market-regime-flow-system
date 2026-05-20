import numpy as np
import pandas as pd

from src.correlation import correlation_distance, latest_rolling_correlation, rolling_correlation_matrix, static_correlation_matrix


def test_static_correlation_and_distance():
    returns = pd.DataFrame(
        {
            "AAA": [0.01, 0.02, 0.03, 0.04],
            "BBB": [0.02, 0.04, 0.06, 0.08],
            "CCC": [0.04, 0.03, 0.02, 0.01],
        }
    )

    corr = static_correlation_matrix(returns)
    distance = correlation_distance(corr)

    assert np.isclose(corr.loc["AAA", "BBB"], 1.0)
    assert np.isclose(distance.loc["AAA", "BBB"], 0.0)
    assert distance.loc["AAA", "CCC"] > 1.0


def test_rolling_correlation_latest_matrix():
    returns = pd.DataFrame(
        {
            "AAA": [0.01, 0.02, 0.03, 0.04],
            "BBB": [0.02, 0.04, 0.06, 0.08],
        },
        index=pd.date_range("2026-01-01", periods=4),
    )

    rolling = rolling_correlation_matrix(returns, window=3)
    latest = latest_rolling_correlation(rolling)

    assert list(latest.columns) == ["AAA", "BBB"]
    assert np.isclose(latest.loc["AAA", "BBB"], 1.0)
