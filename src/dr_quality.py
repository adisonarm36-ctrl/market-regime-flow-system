from __future__ import annotations

import numpy as np
import pandas as pd

from .dr_mapping import normalize_dr_mapping


def calculate_average_traded_value(price_df: pd.DataFrame, volume_df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Calculate latest average traded value over a rolling window."""
    traded_value = price_df.sort_index() * volume_df.sort_index()
    return traded_value.rolling(window, min_periods=1).mean().iloc[-1].rename("average_traded_value_20d")


def calculate_bid_ask_spread_bps(bid_df: pd.DataFrame | None, ask_df: pd.DataFrame | None) -> pd.Series:
    """Calculate latest bid-ask spread in basis points when bid/ask data is available."""
    if bid_df is None or ask_df is None:
        return pd.Series(dtype="float64", name="spread_bps")
    bid = bid_df.sort_index().iloc[-1]
    ask = ask_df.sort_index().iloc[-1]
    mid = (bid + ask) / 2
    return (((ask - bid) / mid.replace(0, np.nan)) * 10_000).rename("spread_bps")


def calculate_volume_consistency(volume_df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Calculate 0-100 volume consistency from rolling coefficient of variation."""
    rolling = volume_df.sort_index().rolling(window, min_periods=2)
    mean = rolling.mean().iloc[-1]
    std = rolling.std().iloc[-1]
    cv = std / mean.replace(0, np.nan)
    return (100 / (1 + cv)).fillna(0).rename("volume_consistency")


def calculate_tracking_correlation(
    dr_price_df: pd.DataFrame,
    underlying_price_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    fx_df: pd.DataFrame | None = None,
    window: int = 60,
) -> pd.Series:
    """Calculate DR tracking correlation with underlying, optionally adjusted by FX series."""
    rows: dict[str, float] = {}
    dr_returns = dr_price_df.sort_index().pct_change()
    underlying_prices = underlying_price_df.sort_index().copy()

    for _, mapping in mapping_df.iterrows():
        dr = mapping["DR_Ticker"]
        underlying = mapping["Underlying_Ticker"]
        if dr not in dr_returns.columns or underlying not in underlying_prices.columns:
            rows[dr] = np.nan
            continue

        adjusted_underlying = underlying_prices[underlying]
        fx_ticker = mapping.get("FX_Ticker")
        if fx_df is not None and pd.notna(fx_ticker) and fx_ticker in fx_df.columns:
            adjusted_underlying = adjusted_underlying * fx_df[fx_ticker]

        underlying_returns = adjusted_underlying.pct_change()
        joined = pd.concat([dr_returns[dr], underlying_returns], axis=1).dropna().tail(window)
        if len(joined) < 2 or joined.iloc[:, 0].std() == 0 or joined.iloc[:, 1].std() == 0:
            rows[dr] = np.nan
        else:
            rows[dr] = joined.iloc[:, 0].corr(joined.iloc[:, 1])

    return pd.Series(rows, name="tracking_correlation")


def calculate_premium_discount(dr_price_df: pd.DataFrame, fair_value_df: pd.DataFrame | None) -> pd.Series:
    """Calculate latest DR premium/discount when fair value data is available."""
    if fair_value_df is None:
        return pd.Series(dtype="float64", name="premium_discount")
    latest_dr = dr_price_df.sort_index().iloc[-1]
    latest_fair = fair_value_df.sort_index().iloc[-1]
    return (latest_dr / latest_fair.replace(0, np.nan) - 1).rename("premium_discount")


def build_dr_quality_table(
    dr_price_df: pd.DataFrame,
    dr_volume_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    underlying_price_df: pd.DataFrame | None = None,
    bid_df: pd.DataFrame | None = None,
    ask_df: pd.DataFrame | None = None,
    fx_df: pd.DataFrame | None = None,
    fair_value_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build DR execution quality metrics. Missing optional data is reported in warning columns."""
    rows = pd.DataFrame({"DR_Ticker": mapping_df["DR_Ticker"].unique()})
    rows = rows.merge(mapping_df, on="DR_Ticker", how="left")

    avg_value = calculate_average_traded_value(dr_price_df, dr_volume_df).rename_axis("DR_Ticker").reset_index()
    volume_consistency = calculate_volume_consistency(dr_volume_df).rename_axis("DR_Ticker").reset_index()
    rows = rows.merge(avg_value, on="DR_Ticker", how="left").merge(volume_consistency, on="DR_Ticker", how="left")

    spread = calculate_bid_ask_spread_bps(bid_df, ask_df)
    rows = rows.merge(spread.rename_axis("DR_Ticker").reset_index(), on="DR_Ticker", how="left")

    if underlying_price_df is not None:
        tracking = calculate_tracking_correlation(dr_price_df, underlying_price_df, mapping_df, fx_df=fx_df)
        rows = rows.merge(tracking.rename_axis("DR_Ticker").reset_index(), on="DR_Ticker", how="left")
    else:
        rows["tracking_correlation"] = np.nan

    premium = calculate_premium_discount(dr_price_df, fair_value_df)
    rows = rows.merge(premium.rename_axis("DR_Ticker").reset_index(), on="DR_Ticker", how="left")

    rows["data_quality_warning"] = rows.apply(_quality_warning, axis=1)
    rows["dr_quality_score"] = calculate_dr_quality_score(rows)
    return rows.sort_values(["Underlying_Ticker", "dr_quality_score"], ascending=[True, False]).reset_index(drop=True)


def calculate_dr_quality_score(dr_quality_df: pd.DataFrame) -> pd.Series:
    """Calculate 0-100 DR execution quality score from available metrics."""
    components = []
    if "average_traded_value_20d" in dr_quality_df.columns:
        components.append(dr_quality_df["average_traded_value_20d"].rank(pct=True) * 100)
    if "volume_consistency" in dr_quality_df.columns:
        components.append(dr_quality_df["volume_consistency"].clip(0, 100))
    if "spread_bps" in dr_quality_df.columns:
        components.append((100 - dr_quality_df["spread_bps"].rank(pct=True) * 100).clip(0, 100))
    if "tracking_correlation" in dr_quality_df.columns:
        components.append(((dr_quality_df["tracking_correlation"].fillna(0) + 1) / 2 * 100).clip(0, 100))
    if not components:
        return pd.Series(0, index=dr_quality_df.index, name="dr_quality_score")
    return pd.concat(components, axis=1).mean(axis=1, skipna=True).fillna(0).rename("dr_quality_score")


def rank_dr_candidates(dr_quality_df: pd.DataFrame) -> pd.DataFrame:
    """Rank DR candidates that reference the same underlying by execution quality."""
    result = dr_quality_df.copy()
    result["execution_rank"] = result.groupby("Underlying_Ticker")["dr_quality_score"].rank(method="first", ascending=False)
    return result.sort_values(["Underlying_Ticker", "execution_rank"]).reset_index(drop=True)


def rank_dr_candidates_by_reference_quality(
    dr_mapping_df: pd.DataFrame,
    dr_liquidity_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Rank Thailand DR/DRx candidates from local reference and optional liquidity data only."""
    mapping = normalize_dr_mapping(dr_mapping_df)
    if mapping.empty:
        return pd.DataFrame(columns=["DR_Ticker", "UnderlyingTicker", "DR_Type", "quality_score", "quality_label", "reasons", "warnings"])
    rows = mapping.copy()
    if dr_liquidity_df is not None and not dr_liquidity_df.empty:
        liquidity_columns = [
            column
            for column in ["Ticker", "average_traded_value_20d", "average_volume_20d", "trading_days_ratio_60d"]
            if column in dr_liquidity_df.columns
        ]
        rows = rows.merge(dr_liquidity_df[liquidity_columns], left_on="DR_Ticker", right_on="Ticker", how="left")

    scores = []
    labels = []
    reasons = []
    warnings = []
    has_liquidity_input = dr_liquidity_df is not None and not dr_liquidity_df.empty
    for _, row in rows.iterrows():
        score = 0.0
        row_reasons: list[str] = []
        row_warnings: list[str] = []
        is_active = _safe_bool(row.get("IsActive", True))
        has_fair_value = _safe_bool(row.get("HasFairValueInput", False))
        if is_active:
            score += 30
            row_reasons.append("active_mapping")
        else:
            row_reasons.append("inactive_mapping")
            row_warnings.append("inactive_dr_reference")

        if pd.notna(row.get("average_traded_value_20d")):
            score += min(35, np.log10(max(float(row["average_traded_value_20d"]), 1)) * 5)
            row_reasons.append("average_traded_value_available")
        if pd.notna(row.get("average_volume_20d")):
            score += min(15, np.log10(max(float(row["average_volume_20d"]), 1)) * 3)
            row_reasons.append("average_volume_available")
        if pd.notna(row.get("trading_days_ratio_60d")):
            score += max(0, min(15, float(row["trading_days_ratio_60d"]) * 15))
            row_reasons.append("trading_days_ratio_available")
        if has_fair_value:
            score += 10
            row_reasons.append("fair_value_input_available")

        if not has_liquidity_input:
            row_warnings.append("limited_confidence_mapping_only")
            label = "Reference Only" if is_active else "Insufficient Data"
        elif has_fair_value:
            label = "Fair Value Supported"
        elif any(reason.endswith("available") for reason in row_reasons):
            label = "Liquidity Supported"
        else:
            row_warnings.append("missing_liquidity_for_dr")
            label = "Insufficient Data"

        scores.append(round(float(score), 2))
        labels.append(label)
        reasons.append(";".join(row_reasons))
        warnings.append(";".join(row_warnings))

    rows["quality_score"] = scores
    rows["quality_label"] = labels
    rows["reasons"] = reasons
    rows["warnings"] = warnings
    rows["data_quality_warning"] = rows["warnings"].map(
        lambda value: f"DR quality skipped: missing optional price/volume data; using reference-only ranking; {value}".strip("; ")
    )
    result = rows.rename(columns={"Underlying_Ticker": "UnderlyingTicker_alias"})
    columns = ["DR_Ticker", "UnderlyingTicker", "DR_Type", "quality_score", "quality_label", "reasons", "warnings", "data_quality_warning"]
    return result[columns].sort_values(["UnderlyingTicker", "quality_score"], ascending=[True, False]).reset_index(drop=True)


def _quality_warning(row: pd.Series) -> str:
    warnings = []
    if pd.isna(row.get("spread_bps")):
        warnings.append("missing_bid_ask_spread")
    if pd.isna(row.get("tracking_correlation")):
        warnings.append("missing_tracking_correlation")
    if pd.isna(row.get("premium_discount")):
        warnings.append("missing_premium_discount")
    return ";".join(warnings)


def _safe_bool(value) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}
