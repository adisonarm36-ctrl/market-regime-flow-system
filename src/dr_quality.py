from __future__ import annotations

import numpy as np
import pandas as pd

from .dr_mapping import normalize_dr_mapping
from .dr_valuation import (
    calculate_dr_fair_value,
    calculate_premium_discount as val_premium_discount,
    calculate_bid_ask_spread_pct,
    calculate_fx_adjusted_underlying_return,
    calculate_tracking_correlation as val_tracking_correlation,
    calculate_tracking_error,
)


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


def rank_dr_candidates_with_execution_quality(
    dr_mapping_df: pd.DataFrame,
    dr_market_data_df: pd.DataFrame | None = None,
    dr_bid_ask_df: pd.DataFrame | None = None,
    fair_value_inputs_df: pd.DataFrame | None = None,
    underlying_prices_df: pd.DataFrame | None = None,
    fx_rates_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Enhanced DR candidate ranking using multiple data dimensions (liquidity, spread, valuation, tracking)."""
    if dr_mapping_df is None or dr_mapping_df.empty:
        return pd.DataFrame(columns=[
            "DR_Ticker", "UnderlyingTicker", "Underlying_Ticker", "IsActive",
            "LiquiditySupported", "SpreadSupported", "FairValueSupported", "TrackingSupported",
            "confidence_level", "quality_label", "warnings", "data_quality_warning",
            "average_traded_value_20d", "volume_consistency", "spread_pct", "spread_bps",
            "fair_value", "premium_discount_pct", "tracking_correlation", "tracking_error",
            "quality_score", "dr_quality_score", "execution_rank"
        ])

    mapping = dr_mapping_df.copy()
    if "UnderlyingTicker" not in mapping.columns and "Underlying_Ticker" in mapping.columns:
        mapping["UnderlyingTicker"] = mapping["Underlying_Ticker"]

    results = []

    # Copy and parse dates safely to avoid SettingWithCopyWarnings
    market_data = dr_market_data_df.copy() if dr_market_data_df is not None else None
    if market_data is not None and "Date" in market_data.columns:
        market_data["Date"] = pd.to_datetime(market_data["Date"])

    bid_ask = dr_bid_ask_df.copy() if dr_bid_ask_df is not None else None
    if bid_ask is not None and "Date" in bid_ask.columns:
        bid_ask["Date"] = pd.to_datetime(bid_ask["Date"])

    und_prices = underlying_prices_df.copy() if underlying_prices_df is not None else None
    if und_prices is not None and "Date" in und_prices.columns:
        und_prices["Date"] = pd.to_datetime(und_prices["Date"])

    fx_rates = fx_rates_df.copy() if fx_rates_df is not None else None
    if fx_rates is not None and "Date" in fx_rates.columns:
        fx_rates["Date"] = pd.to_datetime(fx_rates["Date"])

    for _, row in mapping.iterrows():
        ticker = row["DR_Ticker"]
        underlying = row.get("UnderlyingTicker")
        if pd.isna(underlying) and "Underlying_Ticker" in row:
            underlying = row["Underlying_Ticker"]

        # 1. IsActive
        is_active = _safe_bool(row.get("IsActive", True))

        # Initialize support flags
        liq_supported = False
        spread_supported = False
        fv_supported = False
        track_supported = False

        row_warnings = []

        # Metric values
        avg_value_20d = np.nan
        vol_consistency = np.nan
        spread_pct = np.nan
        fair_value = np.nan
        premium_discount_pct = np.nan
        tracking_corr = np.nan
        tracking_err = np.nan

        # Liquidity Check
        if market_data is not None and not market_data.empty:
            ticker_market = market_data[market_data["DR_Ticker"] == ticker]
            if not ticker_market.empty:
                ticker_market = ticker_market.sort_values("Date")
                val_col = "ValueTraded" if "ValueTraded" in ticker_market.columns else "Value"
                if val_col in ticker_market.columns:
                    avg_value_20d = float(ticker_market[val_col].tail(20).mean())
                else:
                    avg_value_20d = float((ticker_market["Close"] * ticker_market["Volume"]).tail(20).mean())

                if "Volume" in ticker_market.columns:
                    vol_tail = ticker_market["Volume"].tail(20)
                    if len(vol_tail) >= 2:
                        mean_vol = vol_tail.mean()
                        std_vol = vol_tail.std()
                        if mean_vol > 0:
                            cv = std_vol / mean_vol
                            vol_consistency = float(100.0 / (1.0 + cv))
                        else:
                            vol_consistency = 0.0
                    else:
                        vol_consistency = 0.0

                if pd.notna(avg_value_20d) and avg_value_20d > 0:
                    liq_supported = True
            else:
                row_warnings.append("missing_liquidity_for_dr")
        else:
            row_warnings.append("missing_liquidity_for_dr")

        # Bid-Ask Check
        if bid_ask is not None and not bid_ask.empty:
            ticker_spread = bid_ask[bid_ask["DR_Ticker"] == ticker]
            if not ticker_spread.empty:
                ticker_spread = ticker_spread.sort_values("Date")
                latest_row = ticker_spread.iloc[-1]
                bid = float(latest_row["Bid"])
                ask = float(latest_row["Ask"])
                spread_pct = calculate_bid_ask_spread_pct(bid, ask)
                if pd.notna(spread_pct):
                    spread_supported = True
            else:
                row_warnings.append("missing_bid_ask_spread")
        else:
            row_warnings.append("missing_bid_ask_spread")

        # Fair Value Check
        fv_input = None
        if fair_value_inputs_df is not None and not fair_value_inputs_df.empty:
            match = fair_value_inputs_df[fair_value_inputs_df["DR_Ticker"] == ticker]
            if not match.empty:
                fv_input = match.iloc[0]

        if fv_input is not None:
            und_ticker = fv_input["UnderlyingTicker"]
            fx_pair = fv_input["FXPair"]
            ratio = float(fv_input["Ratio"])
            fee_adj = float(fv_input["FeeAdjustmentPct"])

            if und_prices is not None and not und_prices.empty and fx_rates is not None and not fx_rates.empty:
                ticker_und = und_prices[und_prices["UnderlyingTicker"] == und_ticker]
                pair_fx = fx_rates[fx_rates["FXPair"] == fx_pair]

                if not ticker_und.empty and not pair_fx.empty:
                    merged_fv = pd.merge(ticker_und[["Date", "Close"]], pair_fx[["Date", "Rate"]], on="Date").sort_values("Date")
                    if not merged_fv.empty:
                        latest_fv_row = merged_fv.iloc[-1]
                        und_price = float(latest_fv_row["Close"])
                        fx_rate = float(latest_fv_row["Rate"])

                        fair_value = calculate_dr_fair_value(und_price, fx_rate, ratio, fee_adj)

                        if market_data is not None and not market_data.empty:
                            ticker_market = market_data[market_data["DR_Ticker"] == ticker]
                            if not ticker_market.empty:
                                dr_close = float(ticker_market.sort_values("Date").iloc[-1]["Close"])
                                premium_discount_pct = val_premium_discount(dr_close, fair_value)

                        fv_supported = True
                    else:
                        row_warnings.append("missing_underlying_prices_or_fx_rates_data")
                else:
                    row_warnings.append("missing_underlying_prices_or_fx_rates_data")
            else:
                row_warnings.append("missing_underlying_prices_or_fx_rates_data")
        else:
            row_warnings.append("missing_fair_value_mapping")

        # Tracking Check
        if fv_supported and liq_supported:
            und_ticker = fv_input["UnderlyingTicker"]
            fx_pair = fv_input["FXPair"]
            ratio = float(fv_input["Ratio"])

            ticker_market = market_data[market_data["DR_Ticker"] == ticker]
            ticker_und = und_prices[und_prices["UnderlyingTicker"] == und_ticker]
            pair_fx = fx_rates[fx_rates["FXPair"] == fx_pair]

            fx_adj_und = calculate_fx_adjusted_underlying_return(ticker_und, pair_fx, ratio)
            if not fx_adj_und.empty:
                tracking_corr = val_tracking_correlation(ticker_market, fx_adj_und)

                dr_ret = ticker_market.sort_values("Date").copy()
                dr_ret["dr_return"] = dr_ret["Close"].pct_change()
                tracking_err = calculate_tracking_error(dr_ret, fx_adj_und)

                if pd.notna(tracking_corr):
                    track_supported = True
                else:
                    row_warnings.append("missing_tracking_correlation")
            else:
                row_warnings.append("missing_tracking_correlation")
        else:
            row_warnings.append("missing_tracking_correlation")

        # Confidence Levels
        if liq_supported and spread_supported and fv_supported and track_supported:
            confidence_level = "High"
        elif liq_supported and spread_supported:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"

        # Quality Labels
        if is_active and liq_supported and spread_supported:
            quality_label = "Execution Ready"
        elif fv_supported:
            quality_label = "Fair Value Supported"
        elif liq_supported:
            quality_label = "Liquidity Supported"
        elif is_active and ((market_data is not None and not market_data.empty) or (bid_ask is not None and not bid_ask.empty)):
            quality_label = "Reference Only"
        else:
            quality_label = "Insufficient Data"

        results.append({
            "DR_Ticker": ticker,
            "UnderlyingTicker": underlying,
            "Underlying_Ticker": underlying,
            "IsActive": is_active,
            "LiquiditySupported": liq_supported,
            "SpreadSupported": spread_supported,
            "FairValueSupported": fv_supported,
            "TrackingSupported": track_supported,
            "confidence_level": confidence_level,
            "quality_label": quality_label,
            "warnings": ";".join(row_warnings),
            "data_quality_warning": ";".join(row_warnings),
            "average_traded_value_20d": avg_value_20d,
            "volume_consistency": vol_consistency,
            "spread_pct": spread_pct,
            "spread_bps": spread_pct * 100.0 if pd.notna(spread_pct) else np.nan,
            "fair_value": fair_value,
            "premium_discount_pct": premium_discount_pct,
            "tracking_correlation": tracking_corr,
            "tracking_error": tracking_err,
        })

    df_res = pd.DataFrame(results)

    # Scoring components
    components = []
    if "average_traded_value_20d" in df_res.columns and not df_res["average_traded_value_20d"].dropna().empty:
        components.append(df_res["average_traded_value_20d"].rank(pct=True) * 100)
    if "volume_consistency" in df_res.columns and not df_res["volume_consistency"].dropna().empty:
        components.append(df_res["volume_consistency"].clip(0, 100))
    if "spread_bps" in df_res.columns and not df_res["spread_bps"].dropna().empty:
        components.append((100 - df_res["spread_bps"].rank(pct=True) * 100).clip(0, 100))
    if "tracking_correlation" in df_res.columns and not df_res["tracking_correlation"].dropna().empty:
        components.append(((df_res["tracking_correlation"].fillna(0) + 1) / 2 * 100).clip(0, 100))

    if components:
        quality_score = pd.concat(components, axis=1).mean(axis=1, skipna=True).fillna(0)
    else:
        quality_score = pd.Series(0.0, index=df_res.index)

    df_res["quality_score"] = quality_score.round(2)
    df_res["dr_quality_score"] = df_res["quality_score"]

    df_res["execution_rank"] = df_res.groupby("UnderlyingTicker")["quality_score"].rank(method="first", ascending=False)
    df_res = df_res.sort_values(["UnderlyingTicker", "execution_rank"]).reset_index(drop=True)
    return df_res
