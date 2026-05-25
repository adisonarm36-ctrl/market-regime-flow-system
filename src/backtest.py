from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for research-signal backtests."""

    signal_threshold: float = 0.0
    max_gross_exposure: float = 1.0
    max_position_weight: float = 0.25
    rebalance_lag: int = 1
    volatility_window: int = 20
    max_annualized_volatility: float | None = None
    drawdown_guard: float | None = None
    starting_equity: float = 1.0


@dataclass(frozen=True)
class BacktestResult:
    """Container for backtest outputs and data-quality warnings."""

    portfolio: pd.DataFrame
    positions: pd.DataFrame
    instrument_returns: pd.DataFrame
    metrics: pd.DataFrame
    instrument_metrics: pd.DataFrame
    warnings: list[str] = field(default_factory=list)


def calculate_instrument_returns(price_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily instrument returns from a Date x Ticker adjusted-close table."""
    prices = _clean_numeric_table(price_df)
    returns = prices.pct_change(fill_method=None)
    return returns.replace([np.inf, -np.inf], np.nan)


def align_prices_and_signals(price_df: pd.DataFrame, signal_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Align price and signal tables and return warnings for skipped rows or tickers."""
    prices = _clean_numeric_table(price_df)
    signals = _clean_numeric_table(signal_df)
    warnings: list[str] = []

    common_dates = prices.index.intersection(signals.index)
    if len(common_dates) == 0:
        warnings.append("missing_common_dates")

    common_tickers = prices.columns.intersection(signals.columns)
    if len(common_tickers) == 0:
        warnings.append("missing_common_tickers")

    missing_price_tickers = sorted(set(signals.columns) - set(prices.columns))
    if missing_price_tickers:
        warnings.append(f"missing_price_tickers={','.join(missing_price_tickers)}")

    missing_signal_tickers = sorted(set(prices.columns) - set(signals.columns))
    if missing_signal_tickers:
        warnings.append(f"missing_signal_tickers={','.join(missing_signal_tickers)}")

    aligned_prices = prices.loc[common_dates, common_tickers]
    aligned_signals = signals.loc[common_dates, common_tickers]
    return aligned_prices, aligned_signals, warnings


def signals_to_positions(signal_df: pd.DataFrame, config: BacktestConfig | None = None) -> pd.DataFrame:
    """Convert research signal scores into lagged target positions."""
    config = config or BacktestConfig()
    if config.max_gross_exposure < 0:
        raise ValueError("max_gross_exposure must be non-negative")
    if config.max_position_weight <= 0:
        raise ValueError("max_position_weight must be positive")
    if config.rebalance_lag < 0:
        raise ValueError("rebalance_lag must be non-negative")

    signals = _clean_numeric_table(signal_df).fillna(0.0)
    active = signals.where(signals.abs() > config.signal_threshold, 0.0)
    gross_signal = active.abs().sum(axis=1).replace(0, np.nan)
    raw_weights = active.div(gross_signal, axis=0).fillna(0.0)
    capped = raw_weights.clip(lower=-config.max_position_weight, upper=config.max_position_weight)
    positions = _scale_to_gross_exposure(capped, config.max_gross_exposure)
    return positions.shift(config.rebalance_lag).fillna(0.0)


def apply_risk_throttle(
    positions: pd.DataFrame,
    instrument_returns: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply volatility and drawdown throttles to lagged research positions."""
    config = config or BacktestConfig()
    aligned_positions, aligned_returns = positions.align(instrument_returns, join="inner", axis=0)
    aligned_positions, aligned_returns = aligned_positions.align(aligned_returns, join="inner", axis=1)
    throttled = aligned_positions.copy()

    if config.max_annualized_volatility is not None:
        rolling_volatility = aligned_returns.rolling(config.volatility_window, min_periods=2).std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        throttled = throttled.mask(rolling_volatility > config.max_annualized_volatility, 0.0)

    portfolio_returns = (throttled * aligned_returns.fillna(0.0)).sum(axis=1)
    equity = (1.0 + portfolio_returns).cumprod() * config.starting_equity

    if config.drawdown_guard is not None:
        drawdown = equity.div(equity.cummax()).sub(1.0)
        throttle_multiplier = pd.Series(1.0, index=throttled.index)
        throttle_multiplier[drawdown.shift(1).fillna(0.0) <= -abs(config.drawdown_guard)] = 0.0
        throttled = throttled.mul(throttle_multiplier, axis=0)
        portfolio_returns = (throttled * aligned_returns.fillna(0.0)).sum(axis=1)
        equity = (1.0 + portfolio_returns).cumprod() * config.starting_equity

    throttle_state = pd.DataFrame(
        {
            "gross_exposure": throttled.abs().sum(axis=1),
            "equity": equity,
            "portfolio_return": portfolio_returns,
        }
    )
    return throttled, throttle_state


def run_signal_backtest(
    price_df: pd.DataFrame,
    signal_df: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Run a core research-signal backtest without dashboard or pipeline integration."""
    config = config or BacktestConfig()
    prices, signals, warnings = align_prices_and_signals(price_df, signal_df)
    if prices.empty or signals.empty:
        empty = pd.DataFrame()
        metrics = _portfolio_metrics(pd.Series(dtype=float), empty)
        return BacktestResult(empty, empty, empty, metrics, empty, warnings)

    instrument_returns = calculate_instrument_returns(prices)
    positions = signals_to_positions(signals, config)
    throttled_positions, throttle_state = apply_risk_throttle(positions, instrument_returns, config)
    portfolio_returns = throttle_state["portfolio_return"]
    equity = throttle_state["equity"]
    turnover = throttled_positions.diff().abs().sum(axis=1).fillna(throttled_positions.abs().sum(axis=1))
    portfolio = pd.DataFrame(
        {
            "portfolio_return": portfolio_returns,
            "equity": equity,
            "drawdown": equity.div(equity.cummax()).sub(1.0),
            "gross_exposure": throttle_state["gross_exposure"],
            "turnover": turnover,
            "signal_type": "research signal only",
        }
    )

    return BacktestResult(
        portfolio=portfolio,
        positions=throttled_positions,
        instrument_returns=instrument_returns,
        metrics=_portfolio_metrics(portfolio_returns, throttled_positions),
        instrument_metrics=_instrument_metrics(instrument_returns, throttled_positions),
        warnings=warnings,
    )


def _portfolio_metrics(portfolio_returns: pd.Series, positions: pd.DataFrame) -> pd.DataFrame:
    returns = pd.to_numeric(portfolio_returns, errors="coerce").dropna()
    if returns.empty:
        return pd.DataFrame(
            [
                {
                    "total_return": np.nan,
                    "annualized_volatility": np.nan,
                    "max_drawdown": np.nan,
                    "hit_rate": np.nan,
                    "turnover": np.nan,
                    "average_gross_exposure": np.nan,
                    "observations": 0,
                    "signal_type": "research signal only",
                }
            ]
        )

    equity = (1.0 + returns).cumprod()
    turnover = positions.diff().abs().sum(axis=1).fillna(positions.abs().sum(axis=1)) if not positions.empty else pd.Series(dtype=float)
    return pd.DataFrame(
        [
            {
                "total_return": equity.iloc[-1] - 1.0,
                "annualized_volatility": returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR),
                "max_drawdown": equity.div(equity.cummax()).sub(1.0).min(),
                "hit_rate": returns.gt(0).mean(),
                "turnover": turnover.mean() if not turnover.empty else np.nan,
                "average_gross_exposure": positions.abs().sum(axis=1).mean() if not positions.empty else np.nan,
                "observations": int(returns.shape[0]),
                "signal_type": "research signal only",
            }
        ]
    )


def _instrument_metrics(instrument_returns: pd.DataFrame, positions: pd.DataFrame) -> pd.DataFrame:
    if instrument_returns.empty or positions.empty:
        return pd.DataFrame(columns=["Ticker", "total_return", "annualized_volatility", "hit_rate", "average_weight"])

    rows = []
    for ticker in instrument_returns.columns:
        returns = instrument_returns[ticker].dropna()
        rows.append(
            {
                "Ticker": ticker,
                "total_return": (1.0 + returns).prod() - 1.0 if not returns.empty else np.nan,
                "annualized_volatility": returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) if not returns.empty else np.nan,
                "hit_rate": returns.gt(0).mean() if not returns.empty else np.nan,
                "average_weight": positions[ticker].mean() if ticker in positions.columns else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _clean_numeric_table(df: pd.DataFrame) -> pd.DataFrame:
    table = df.copy()
    table.index = pd.to_datetime(table.index)
    table = table.sort_index()
    return table.apply(pd.to_numeric, errors="coerce")


def _scale_to_gross_exposure(weights: pd.DataFrame, max_gross_exposure: float) -> pd.DataFrame:
    gross = weights.abs().sum(axis=1)
    scale = pd.Series(1.0, index=weights.index)
    over_limit = gross > max_gross_exposure
    scale.loc[over_limit] = max_gross_exposure / gross.loc[over_limit]
    return weights.mul(scale, axis=0)
