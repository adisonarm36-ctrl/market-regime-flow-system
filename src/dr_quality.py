from __future__ import annotations

import numpy as np
import pandas as pd

from .dr_valuation import (
    calculate_dr_fair_value,
    calculate_premium_discount as val_premium_discount,
    calculate_bid_ask_spread_pct,
    calculate_fx_adjusted_underlying_return,
    calculate_tracking_correlation as val_tracking_correlation,
    calculate_tracking_error as val_tracking_error,
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


def _quality_warning(row: pd.Series) -> str:
    warnings = []
    if pd.isna(row.get("spread_bps")):
        warnings.append("missing_bid_ask_spread")
    if pd.isna(row.get("tracking_correlation")):
        warnings.append("missing_tracking_correlation")
    if pd.isna(row.get("premium_discount")):
        warnings.append("missing_premium_discount")
    return ";".join(warnings)


# ==========================================
# Phase 5A: Enhanced Execution Quality logic
# ==========================================

def rank_dr_candidates_with_execution_quality(
    dr_mapping_df: pd.DataFrame,
    dr_market_data_df: pd.DataFrame | None = None,
    dr_bid_ask_df: pd.DataFrame | None = None,
    fair_value_inputs_df: pd.DataFrame | None = None,
    underlying_prices_df: pd.DataFrame | None = None,
    fx_rates_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Rank DR/DRx candidates by detailed execution quality metrics."""
    # Normalize inputs
    mapping = dr_mapping_df.copy()
    if "Underlying_Ticker" in mapping.columns and "UnderlyingTicker" not in mapping.columns:
        mapping = mapping.rename(columns={"Underlying_Ticker": "UnderlyingTicker"})
        
    results = []
    
    for _, mapping_row in mapping.iterrows():
        dr_ticker = mapping_row["DR_Ticker"]
        underlying = mapping_row["UnderlyingTicker"]
        
        # Determine DR Type
        dr_type = "DRx" if "DRX" in str(dr_ticker).upper() or str(dr_ticker).upper().endswith("X") else "DR"
        
        # 1. Retrieve IsActive directly from mapping (default to True if not specified)
        is_active = True
        if "IsActive" in mapping.columns:
            val = mapping_row["IsActive"]
            if pd.notna(val):
                is_active = bool(val)
                
        # Defaults
        avg_value = 0.0
        avg_vol = 0.0
        trading_days_ratio = 0.0
        bid_ask_spread_pct = np.nan
        premium_discount_pct = np.nan
        tracking_correlation = np.nan
        tracking_error = np.nan
        has_fair_value_input = False
        
        # Support Indicators
        liquidity_supported = False
        spread_supported = False
        fair_value_supported = False
        tracking_supported = False
        
        reasons = []
        warnings = []
        
        # 2. Market / Liquidity Data
        market_filtered = pd.DataFrame()
        if dr_market_data_df is not None and not dr_market_data_df.empty and "DR_Ticker" in dr_market_data_df.columns:
            market_filtered = dr_market_data_df[dr_market_data_df["DR_Ticker"] == dr_ticker].copy()
            if not market_filtered.empty:
                market_filtered["Date"] = pd.to_datetime(market_filtered["Date"])
                market_filtered = market_filtered.sort_values("Date")
                
                # Liquidity
                recent_mkt = market_filtered.tail(20)
                avg_vol = float(recent_mkt["Volume"].mean())
                if "ValueTraded" in recent_mkt.columns:
                    avg_value = float(recent_mkt["ValueTraded"].mean())
                else:
                    avg_value = float((recent_mkt["Close"] * recent_mkt["Volume"]).mean())
                
                # Trading Days Ratio (out of 60)
                active_days = (market_filtered["Volume"].tail(60) > 0).sum()
                trading_days_ratio = float(active_days / 60.0)
                
                # LiquiditySupported logic: value >= 10,000 and trading days ratio >= 0.1
                liquidity_supported = avg_value >= 10000.0 and trading_days_ratio >= 0.1
                reasons.append(f"liquidity_computed(value={avg_value:.1f},days_ratio={trading_days_ratio:.2f})")
            else:
                warnings.append("missing_market_data_rows")
        else:
            warnings.append("missing_market_data")
            
        # 3. Bid-Ask Spread Data
        bid_ask_filtered = pd.DataFrame()
        if dr_bid_ask_df is not None and not dr_bid_ask_df.empty and "DR_Ticker" in dr_bid_ask_df.columns:
            bid_ask_filtered = dr_bid_ask_df[dr_bid_ask_df["DR_Ticker"] == dr_ticker].copy()
            if not bid_ask_filtered.empty:
                bid_ask_filtered["Date"] = pd.to_datetime(bid_ask_filtered["Date"])
                recent_ba = bid_ask_filtered.sort_values("Date").tail(20)
                spreads = recent_ba.apply(lambda r: calculate_bid_ask_spread_pct(r["Bid"], r["Ask"]), axis=1)
                bid_ask_spread_pct = float(spreads.mean())
                
                # SpreadSupported logic
                spread_supported = not pd.isna(bid_ask_spread_pct)
                reasons.append(f"spread_computed(avg={bid_ask_spread_pct:.3f}%)")
            else:
                warnings.append("missing_bid_ask_rows")
        else:
            warnings.append("missing_bid_ask_data")
            
        # 4. Fair Value & Premium/Discount, Tracking Error
        if fair_value_inputs_df is not None and not fair_value_inputs_df.empty and "DR_Ticker" in fair_value_inputs_df.columns:
            fv_match = fair_value_inputs_df[fair_value_inputs_df["DR_Ticker"] == dr_ticker]
            if not fv_match.empty:
                fv_input = fv_match.iloc[0]
                ratio = float(fv_input["Ratio"])
                fx_pair = fv_input["FXPair"]
                fee_adj = float(fv_input.get("FeeAdjustmentPct", 0.0))
                
                # Validate RatioConvention
                ratio_conv = fv_input.get("RatioConvention", "DR_per_Underlying")
                if ratio_conv != "DR_per_Underlying":
                    warnings.append(f"unsupported_ratio_convention({ratio_conv})")
                    has_fair_value_input = False
                else:
                    has_fair_value_input = True
                
                if has_fair_value_input:
                    # Try to calculate Fair Value and tracking metrics
                    if underlying_prices_df is not None and not underlying_prices_df.empty and fx_rates_df is not None and not fx_rates_df.empty:
                        und_prices = underlying_prices_df[underlying_prices_df["UnderlyingTicker"] == underlying].copy()
                        fx_rates = fx_rates_df[fx_rates_df["FXPair"] == fx_pair].copy()
                        
                        if not und_prices.empty and not fx_rates.empty:
                            und_prices["Date"] = pd.to_datetime(und_prices["Date"])
                            fx_rates["Date"] = pd.to_datetime(fx_rates["Date"])
                            
                            # Calculate daily adjusted prices
                            fx_adj_df = calculate_fx_adjusted_underlying_return(und_prices, fx_rates, ratio)
                            
                            if not fx_adj_df.empty and not market_filtered.empty:
                                # Tracking Correlation
                                tracking_correlation = val_tracking_correlation(market_filtered, fx_adj_df)
                                tracking_supported = not pd.isna(tracking_correlation)
                                
                                # Tracking Error
                                mkt_ret = market_filtered.sort_values("Date").copy()
                                mkt_ret["dr_return"] = mkt_ret["Close"].pct_change()
                                tracking_error = val_tracking_error(mkt_ret, fx_adj_df)
                                
                                # Premium/Discount at latest available date
                                latest_mkt = market_filtered.sort_values("Date").iloc[-1]
                                latest_date = latest_mkt["Date"]
                                latest_dr_close = latest_mkt["Close"]
                                
                                # Find matched adjusted underlying price for latest date
                                latest_fx_adj = fx_adj_df[fx_adj_df["Date"] == latest_date]
                                if not latest_fx_adj.empty:
                                    fair_val = latest_fx_adj.iloc[0]["fx_adjusted_price"]
                                    premium_discount_pct = val_premium_discount(latest_dr_close, fair_val)
                                    fair_value_supported = not pd.isna(premium_discount_pct)
                                    reasons.append(f"fair_value_computed(premium={premium_discount_pct:.2f}%)")
                                else:
                                    warnings.append("missing_aligned_date_for_fair_value")
                            else:
                                warnings.append("missing_market_or_fx_adjusted_prices_overlap")
                        else:
                            warnings.append("missing_underlying_prices_or_fx_rates_rows")
                    else:
                        warnings.append("missing_underlying_prices_or_fx_rates_data")
            else:
                warnings.append("missing_fair_value_mapping_for_ticker")
        else:
            warnings.append("missing_fair_value_inputs_data")
            
        # 5. Determine Confidence Level
        # - High: requires liquidity, spread, fair value, and tracking data all present
        # - Medium: requires liquidity and spread data
        # - Low: otherwise
        if liquidity_supported and spread_supported and fair_value_supported and tracking_supported:
            confidence_level = "High"
        elif liquidity_supported and spread_supported:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"
            
        # 6. Determine Quality Label
        # - Execution Ready: IsActive == True AND LiquiditySupported == True AND SpreadSupported == True
        # - Fair Value Supported: FairValueSupported == True
        # - Liquidity Supported: LiquiditySupported == True
        # - Reference Only: average_traded_value_20d > 0 OR SpreadSupported == True
        # - Insufficient Data: Fallback
        if is_active and liquidity_supported and spread_supported:
            quality_label = "Execution Ready"
        elif fair_value_supported:
            quality_label = "Fair Value Supported"
        elif liquidity_supported:
            quality_label = "Liquidity Supported"
        elif avg_value > 0 or spread_supported:
            quality_label = "Reference Only"
        else:
            quality_label = "Insufficient Data"
            
        # Calculate custom quality score 0 - 100
        score = 10.0  # Base score for reference
        if liquidity_supported:
            score += 20.0
            if avg_value > 0:
                score += min(20.0, np.log10(avg_value) * 3.0)
        if spread_supported:
            score += max(0.0, 30.0 - bid_ask_spread_pct * 15.0)
        if tracking_supported:
            score += max(0.0, tracking_correlation * 20.0)
        if is_active:
            score += 10.0
        else:
            score = max(5.0, score - 20.0) # Penalty for inactive DR
            
        quality_score = float(np.clip(score, 0.0, 100.0))
        
        results.append({
            "DR_Ticker": dr_ticker,
            "UnderlyingTicker": underlying,
            "Underlying_Ticker": underlying,
            "DR_Type": dr_type,
            "quality_score": quality_score,
            "dr_quality_score": quality_score,
            "quality_label": quality_label,
            "average_traded_value_20d": avg_value,
            "average_volume_20d": avg_vol,
            "trading_days_ratio_60d": trading_days_ratio,
            "bid_ask_spread_pct": bid_ask_spread_pct,
            "premium_discount_pct": premium_discount_pct,
            "tracking_correlation": tracking_correlation,
            "tracking_error": tracking_error,
            "HasFairValueInput": has_fair_value_input,
            "IsActive": is_active,
            "LiquiditySupported": liquidity_supported,
            "SpreadSupported": spread_supported,
            "FairValueSupported": fair_value_supported,
            "TrackingSupported": tracking_supported,
            "reasons": ";".join(reasons),
            "warnings": ";".join(warnings),
            "data_quality_warning": ";".join(warnings),
            "confidence_level": confidence_level
        })
        
    res_df = pd.DataFrame(results)
    
    # Add execution rank grouped by UnderlyingTicker
    if not res_df.empty:
        res_df["execution_rank"] = res_df.groupby("UnderlyingTicker")["quality_score"].rank(method="first", ascending=False).astype(int)
        res_df = res_df.sort_values(["UnderlyingTicker", "execution_rank"]).reset_index(drop=True)
    else:
        res_df = pd.DataFrame(columns=[
            "DR_Ticker", "UnderlyingTicker", "Underlying_Ticker", "DR_Type", "quality_score", "dr_quality_score", "quality_label",
            "average_traded_value_20d", "average_volume_20d", "trading_days_ratio_60d",
            "bid_ask_spread_pct", "premium_discount_pct", "tracking_correlation", "tracking_error",
            "HasFairValueInput", "IsActive", "LiquiditySupported", "SpreadSupported",
            "FairValueSupported", "TrackingSupported", "reasons", "warnings", "data_quality_warning", "confidence_level", "execution_rank"
        ])
        
    return res_df
