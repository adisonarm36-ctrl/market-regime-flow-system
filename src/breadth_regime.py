from __future__ import annotations

import pandas as pd


REGIME_LABELS = {
    "strong_bull": "Strong Bull",
    "bull": "Bull",
    "neutral": "Neutral",
    "bear_warning": "Bear Warning",
    "bear": "Bear",
}


def classify_regime(score: float, thresholds: dict[str, float] | None = None) -> str:
    """Classify a breadth score into a market regime label."""
    thresholds = thresholds or {
        "strong_bull": 75,
        "bull": 60,
        "neutral": 45,
        "bear_warning": 30,
    }
    if score >= thresholds["strong_bull"]:
        return REGIME_LABELS["strong_bull"]
    if score >= thresholds["bull"]:
        return REGIME_LABELS["bull"]
    if score >= thresholds["neutral"]:
        return REGIME_LABELS["neutral"]
    if score >= thresholds["bear_warning"]:
        return REGIME_LABELS["bear_warning"]
    return REGIME_LABELS["bear"]


def add_regime(summary_df: pd.DataFrame, score_column: str = "breadth_score") -> pd.DataFrame:
    """Add market regime labels to a breadth summary table."""
    result = summary_df.copy()
    result["regime"] = result[score_column].map(classify_regime)
    return result
