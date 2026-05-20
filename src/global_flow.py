from __future__ import annotations

import numpy as np
import pandas as pd


FLOW_LABELS = {
    "strong_inflow": "Strong Inflow",
    "moderate_inflow": "Moderate Inflow",
    "neutral": "Neutral",
    "moderate_outflow": "Moderate Outflow",
    "strong_outflow": "Strong Outflow",
}


def calculate_returns(price_df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    """Calculate latest multi-window simple returns for each ticker."""
    windows = windows or [1, 5, 20, 60]
    metrics = pd.DataFrame(index=price_df.columns)
    sorted_prices = price_df.sort_index()
    for window in windows:
        metrics[f"return_{window}d"] = sorted_prices.pct_change(window).iloc[-1]
    return metrics


def calculate_volume_zscore(volume_df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Calculate latest rolling volume z-score for each ticker."""
    sorted_volume = volume_df.sort_index()
    rolling_mean = sorted_volume.rolling(window).mean()
    rolling_std = sorted_volume.rolling(window).std(ddof=0)
    zscore = (sorted_volume - rolling_mean) / rolling_std.replace(0, np.nan)
    return zscore.iloc[-1].rename("volume_zscore")


def calculate_relative_strength(price_df: pd.DataFrame, benchmark_ticker: str, window: int = 20) -> pd.Series:
    """Calculate latest relative strength versus a benchmark ticker."""
    if benchmark_ticker not in price_df.columns:
        raise ValueError(f"Benchmark ticker not found: {benchmark_ticker}")
    returns = price_df.sort_index().pct_change(window)
    relative_strength = returns.subtract(returns[benchmark_ticker], axis=0)
    return relative_strength.iloc[-1].rename("relative_strength")


def calculate_flow_score(metrics_df: pd.DataFrame) -> pd.Series:
    """Calculate a 0-100 price-based flow proxy score from return, volume, and relative strength metrics."""
    metrics = metrics_df.copy()
    return_columns = [column for column in metrics.columns if column.startswith("return_")]
    if not return_columns:
        raise ValueError("No return_* columns available for flow scoring")

    return_component = metrics[return_columns].mean(axis=1, skipna=True).rank(pct=True) * 100

    components = [return_component.rename("return_component")]
    if "volume_zscore" in metrics.columns:
        components.append(metrics["volume_zscore"].rank(pct=True).mul(100).rename("volume_component"))
    if "relative_strength" in metrics.columns:
        components.append(metrics["relative_strength"].rank(pct=True).mul(100).rename("relative_strength_component"))

    component_df = pd.concat(components, axis=1)
    return component_df.mean(axis=1, skipna=True).fillna(50).rename("flow_score")


def classify_flow(score: float, thresholds: dict[str, float] | None = None) -> str:
    """Classify a price-based flow proxy score."""
    thresholds = thresholds or {
        "strong_inflow": 75,
        "moderate_inflow": 60,
        "moderate_outflow": 40,
        "strong_outflow": 25,
    }
    if score >= thresholds["strong_inflow"]:
        return FLOW_LABELS["strong_inflow"]
    if score >= thresholds["moderate_inflow"]:
        return FLOW_LABELS["moderate_inflow"]
    if score <= thresholds["strong_outflow"]:
        return FLOW_LABELS["strong_outflow"]
    if score <= thresholds["moderate_outflow"]:
        return FLOW_LABELS["moderate_outflow"]
    return FLOW_LABELS["neutral"]


def build_flow_table(
    price_df: pd.DataFrame,
    volume_df: pd.DataFrame | None = None,
    benchmark_ticker: str | None = None,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Build ticker-level flow proxy metrics and classifications."""
    metrics = calculate_returns(price_df, windows)
    if volume_df is not None:
        metrics = metrics.join(calculate_volume_zscore(volume_df), how="left")
    if benchmark_ticker is not None:
        metrics = metrics.join(calculate_relative_strength(price_df, benchmark_ticker), how="left")
    metrics["flow_score"] = calculate_flow_score(metrics)
    metrics["flow_classification"] = metrics["flow_score"].map(classify_flow)
    metrics["signal_type"] = "price-based flow proxy"
    return metrics.reset_index(names="Ticker")
