from __future__ import annotations

import pandas as pd


def detect_high_correlation_pairs(correlation_df: pd.DataFrame, threshold: float = 0.85) -> pd.DataFrame:
    """Detect instrument pairs with correlation at or above a threshold."""
    rows = []
    columns = list(correlation_df.columns)
    for i, left in enumerate(columns):
        for right in columns[i + 1 :]:
            corr = correlation_df.loc[left, right]
            if pd.notna(corr) and corr >= threshold:
                rows.append({"Ticker_A": left, "Ticker_B": right, "correlation": corr})
    return pd.DataFrame(rows).sort_values("correlation", ascending=False).reset_index(drop=True) if rows else pd.DataFrame(columns=["Ticker_A", "Ticker_B", "correlation"])


def select_preferred_instrument(candidates_df: pd.DataFrame) -> pd.Series:
    """Select the preferred instrument using momentum, liquidity, spread, and trend quality."""
    if "Ticker" not in candidates_df.columns:
        raise ValueError("candidates_df must include Ticker")

    data = candidates_df.copy()
    data["_momentum"] = data.get("momentum_score", 0)
    data["_liquidity"] = data.get("liquidity", data.get("average_traded_value_20d", 0))
    data["_spread"] = data.get("spread_bps", 0)
    data["_trend"] = data.get("trend_quality", 0)
    ranked = data.sort_values(["_momentum", "_liquidity", "_trend", "_spread"], ascending=[False, False, False, True])
    return ranked.iloc[0].drop(labels=[column for column in ranked.columns if column.startswith("_")])


def detect_redundant_instruments_inside_cluster(
    cluster_labels: pd.Series,
    correlation_df: pd.DataFrame,
    threshold: float = 0.85,
) -> pd.DataFrame:
    """Detect highly correlated instrument pairs inside the same cluster."""
    pairs = detect_high_correlation_pairs(correlation_df, threshold)
    if pairs.empty:
        return pairs.assign(cluster=pd.Series(dtype="object"))

    cluster_lookup = cluster_labels.to_dict()
    rows = []
    for _, row in pairs.iterrows():
        left_cluster = cluster_lookup.get(row["Ticker_A"])
        right_cluster = cluster_lookup.get(row["Ticker_B"])
        if left_cluster == right_cluster:
            record = row.to_dict()
            record["cluster"] = left_cluster
            rows.append(record)
    return pd.DataFrame(rows)


def redundancy_report(
    correlation_df: pd.DataFrame,
    instrument_metrics_df: pd.DataFrame,
    threshold: float = 0.85,
) -> pd.DataFrame:
    """Build a redundancy report with preferred instruments for highly correlated pairs."""
    pairs = detect_high_correlation_pairs(correlation_df, threshold)
    if pairs.empty:
        return pd.DataFrame(columns=["Ticker_A", "Ticker_B", "correlation", "preferred_ticker", "redundant_ticker", "reason"])
    if "Ticker" not in instrument_metrics_df.columns:
        raise ValueError("instrument_metrics_df must include Ticker")

    rows = []
    metrics = instrument_metrics_df.set_index("Ticker", drop=False)
    for _, pair in pairs.iterrows():
        tickers = [pair["Ticker_A"], pair["Ticker_B"]]
        available = [ticker for ticker in tickers if ticker in metrics.index]
        if len(available) < 2:
            rows.append({**pair.to_dict(), "preferred_ticker": None, "redundant_ticker": None, "reason": "Missing instrument metrics"})
            continue
        candidates = metrics.loc[available].reset_index(drop=True)
        preferred = select_preferred_instrument(candidates)
        redundant = [ticker for ticker in tickers if ticker != preferred["Ticker"]][0]
        rows.append(
            {
                **pair.to_dict(),
                "preferred_ticker": preferred["Ticker"],
                "redundant_ticker": redundant,
                "reason": "Preferred by higher momentum, liquidity, trend quality, and lower spread",
            }
        )
    return pd.DataFrame(rows)
