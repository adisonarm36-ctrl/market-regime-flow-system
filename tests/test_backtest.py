import numpy as np
import pandas as pd

from src.backtest import (
    BacktestConfig,
    align_prices_and_signals,
    calculate_instrument_returns,
    run_signal_backtest,
    signals_to_positions,
)


def test_backtest_return_alignment_uses_lagged_positions():
    prices = pd.DataFrame(
        {"AAA": [100.0, 110.0, 121.0], "BBB": [50.0, 50.0, 55.0]},
        index=pd.date_range("2026-01-01", periods=3),
    )
    signals = pd.DataFrame(
        {"AAA": [1.0, 1.0, 1.0], "BBB": [0.0, 0.0, 0.0]},
        index=prices.index,
    )

    result = run_signal_backtest(prices, signals, BacktestConfig(max_position_weight=1.0))

    assert result.positions["AAA"].iloc[0] == 0.0
    assert result.positions["AAA"].iloc[1] == 1.0
    assert np.isclose(result.portfolio["portfolio_return"].iloc[1], 0.10)


def test_signals_to_positions_respects_position_and_exposure_limits():
    signals = pd.DataFrame(
        {"AAA": [100.0], "BBB": [80.0], "CCC": [60.0]},
        index=[pd.Timestamp("2026-01-01")],
    )
    config = BacktestConfig(max_gross_exposure=0.6, max_position_weight=0.25, rebalance_lag=0)

    positions = signals_to_positions(signals, config)

    assert positions.abs().sum(axis=1).iloc[0] <= 0.6
    assert positions.abs().max(axis=1).iloc[0] <= 0.25


def test_risk_throttle_reduces_high_volatility_exposure():
    dates = pd.date_range("2026-01-01", periods=6)
    prices = pd.DataFrame(
        {"AAA": [100.0, 130.0, 90.0, 140.0, 80.0, 160.0]},
        index=dates,
    )
    signals = pd.DataFrame({"AAA": [1.0] * len(dates)}, index=dates)
    config = BacktestConfig(
        max_position_weight=1.0,
        volatility_window=2,
        max_annualized_volatility=0.10,
    )

    result = run_signal_backtest(prices, signals, config)

    assert result.positions["AAA"].iloc[-1] == 0.0


def test_missing_signal_or_price_data_is_reported_and_skipped():
    dates = pd.date_range("2026-01-01", periods=3)
    prices = pd.DataFrame({"AAA": [100.0, 101.0, 102.0]}, index=dates)
    signals = pd.DataFrame({"AAA": [1.0, 1.0, 1.0], "MISSING": [1.0, 1.0, 1.0]}, index=dates)

    aligned_prices, aligned_signals, warnings = align_prices_and_signals(prices, signals)

    assert "MISSING" not in aligned_prices.columns
    assert "MISSING" not in aligned_signals.columns
    assert "missing_price_tickers=MISSING" in warnings


def test_backtest_metrics_include_research_signal_label_and_exposure():
    dates = pd.date_range("2026-01-01", periods=4)
    prices = pd.DataFrame({"AAA": [100.0, 105.0, 110.0, 115.0]}, index=dates)
    signals = pd.DataFrame({"AAA": [1.0, 1.0, 1.0, 1.0]}, index=dates)

    result = run_signal_backtest(prices, signals, BacktestConfig(max_position_weight=1.0))
    metrics = result.metrics.iloc[0]

    assert metrics["signal_type"] == "research signal only"
    assert metrics["observations"] == 4
    assert metrics["average_gross_exposure"] > 0
    assert metrics["total_return"] > 0


def test_calculate_instrument_returns_handles_non_numeric_values():
    prices = pd.DataFrame(
        {"AAA": [100.0, "bad", 110.0]},
        index=pd.date_range("2026-01-01", periods=3),
    )

    returns = calculate_instrument_returns(prices)

    assert returns["AAA"].isna().sum() >= 1
