import numpy as np
import pandas as pd
import pytest

from src.dr_quality import rank_dr_candidates_with_execution_quality
from src.topdown_pipeline import run_topdown_pipeline


def test_inactive_dr_cannot_be_execution_ready():
    # Setup mapping with IsActive: False
    mapping_df = pd.DataFrame([
        {"DR_Ticker": "DEMO_INACTIVE", "UnderlyingTicker": "UND_A", "IsActive": False},
        {"DR_Ticker": "DEMO_ACTIVE", "UnderlyingTicker": "UND_A", "IsActive": True}
    ])
    
    # Setup rich mock market data to make them otherwise eligible
    dates = pd.date_range("2026-05-01", periods=20)
    
    # 20 rows of market data to support liquidity (Value > 10,000, 20 days)
    market_rows = []
    for date in dates:
        for ticker in ["DEMO_INACTIVE", "DEMO_ACTIVE"]:
            market_rows.append({
                "Date": date,
                "DR_Ticker": ticker,
                "Open": 10.0,
                "High": 10.5,
                "Low": 9.5,
                "Close": 10.0,
                "Volume": 2000,      # Traded Value = 20,000
                "ValueTraded": 20000
            })
    market_df = pd.DataFrame(market_rows)
    
    # Bid-Ask data to support spread
    bid_ask_rows = []
    for date in dates:
        for ticker in ["DEMO_INACTIVE", "DEMO_ACTIVE"]:
            bid_ask_rows.append({
                "Date": date,
                "DR_Ticker": ticker,
                "Bid": 9.95,
                "Ask": 10.05,
                "BidSize": 100,
                "AskSize": 100
            })
    bid_ask_df = pd.DataFrame(bid_ask_rows)
    
    # Run the quality engine
    res = rank_dr_candidates_with_execution_quality(
        dr_mapping_df=mapping_df,
        dr_market_data_df=market_df,
        dr_bid_ask_df=bid_ask_df
    )
    
    # DEMO_ACTIVE must be Execution Ready (IsActive=True, liquidity supported, spread supported)
    active_row = res[res["DR_Ticker"] == "DEMO_ACTIVE"].iloc[0]
    assert active_row["quality_label"] == "Execution Ready"
    
    # DEMO_INACTIVE cannot be Execution Ready despite high liquidity/spreads, because IsActive=False
    inactive_row = res[res["DR_Ticker"] == "DEMO_INACTIVE"].iloc[0]
    assert inactive_row["quality_label"] != "Execution Ready"
    assert inactive_row["quality_label"] == "Liquidity Supported"  # Fallback label


def test_confidence_level_buckets():
    # 1. Mapping-only DR
    mapping_df = pd.DataFrame([
        {"DR_Ticker": "MAPPING_ONLY", "UnderlyingTicker": "UND_A", "IsActive": True}
    ])
    
    res_low = rank_dr_candidates_with_execution_quality(
        dr_mapping_df=mapping_df,
        dr_market_data_df=None,
        dr_bid_ask_df=None
    )
    # Must be Low confidence due to no transaction/spread/valuation data
    assert res_low.iloc[0]["confidence_level"] == "Low"
    assert res_low.iloc[0]["quality_label"] == "Insufficient Data"

    # 2. Liquidity + Spread present but no FV -> Medium confidence
    dates = pd.date_range("2026-05-01", periods=20)
    market_rows = []
    for i, date in enumerate(dates):
        market_rows.append({
            "Date": date,
            "DR_Ticker": "MED_CONF",
            "Open": 10.0, "High": 10.5, "Low": 9.5, "Close": 10.0 + i * 0.1,
            "Volume": 2000, "ValueTraded": 20000
        })
    market_df = pd.DataFrame(market_rows)
    
    bid_ask_rows = []
    for date in dates:
        bid_ask_rows.append({
            "Date": date,
            "DR_Ticker": "MED_CONF",
            "Bid": 9.9, "Ask": 10.1, "BidSize": 100, "AskSize": 100
        })
    bid_ask_df = pd.DataFrame(bid_ask_rows)
    
    mapping_med = pd.DataFrame([{"DR_Ticker": "MED_CONF", "UnderlyingTicker": "UND_A", "IsActive": True}])
    
    res_med = rank_dr_candidates_with_execution_quality(
        dr_mapping_df=mapping_med,
        dr_market_data_df=market_df,
        dr_bid_ask_df=bid_ask_df
    )
    assert res_med.iloc[0]["confidence_level"] == "Medium"
    
    # 3. High confidence -> requires all 4 layers (liquidity, spreads, fair value, and tracking)
    fair_value_inputs_df = pd.DataFrame([{
        "DR_Ticker": "MED_CONF",
        "UnderlyingTicker": "UND_A",
        "UnderlyingCurrency": "USD",
        "DR_Currency": "THB",
        "Ratio": 10.0,
        "FXPair": "USD/THB",
        "FeeAdjustmentPct": 0.001,
        "RatioConvention": "DR_per_Underlying"
    }])
    underlying_prices_df = pd.DataFrame([
        {"Date": d, "UnderlyingTicker": "UND_A", "Close": 1.0 + i * 0.01, "Currency": "USD"} for i, d in enumerate(dates)
    ])
    fx_rates_df = pd.DataFrame([
        {"Date": d, "FXPair": "USD/THB", "Rate": 35.0} for d in dates
    ])
    
    res_high = rank_dr_candidates_with_execution_quality(
        dr_mapping_df=mapping_med,
        dr_market_data_df=market_df,
        dr_bid_ask_df=bid_ask_df,
        fair_value_inputs_df=fair_value_inputs_df,
        underlying_prices_df=underlying_prices_df,
        fx_rates_df=fx_rates_df
    )
    assert res_high.iloc[0]["confidence_level"] == "High"


def test_missing_fx_graceful_warning():
    mapping_df = pd.DataFrame([
        {"DR_Ticker": "DEMO_DR_A", "UnderlyingTicker": "UND_A", "IsActive": True}
    ])
    dates = pd.date_range("2026-05-01", periods=10)
    market_df = pd.DataFrame([
        {"Date": d, "DR_Ticker": "DEMO_DR_A", "Open": 10, "High": 10, "Low": 10, "Close": 10, "Volume": 100, "ValueTraded": 1000} for d in dates
    ])
    
    # Fair value mappings exist, but underlying prices are empty or fx_rates are None
    fair_value_inputs_df = pd.DataFrame([{
        "DR_Ticker": "DEMO_DR_A",
        "UnderlyingTicker": "UND_A",
        "UnderlyingCurrency": "USD",
        "DR_Currency": "THB",
        "Ratio": 10.0,
        "FXPair": "USD/THB",
        "FeeAdjustmentPct": 0.0,
        "RatioConvention": "DR_per_Underlying"
    }])
    
    # Run quality ranking with missing FX rates
    res = rank_dr_candidates_with_execution_quality(
        dr_mapping_df=mapping_df,
        dr_market_data_df=market_df,
        fair_value_inputs_df=fair_value_inputs_df,
        underlying_prices_df=None,  # missing
        fx_rates_df=None  # missing
    )
    
    # Verify it does not crash
    assert len(res) == 1
    # Verify warning about missing underlying prices/fx rates is logged
    assert "missing_underlying_prices_or_fx_rates_data" in res.iloc[0]["warnings"]
    # Check that FairValueSupported and TrackingSupported are False
    assert res.iloc[0]["FairValueSupported"] == False
    assert res.iloc[0]["TrackingSupported"] == False


def test_pipeline_smoke_test_no_dr_quality():
    # Verify that run_topdown_pipeline runs without crash when all DR specific quality params are omitted
    prices = pd.DataFrame([
        {"Date": "2026-05-20", "Ticker": "SPY", "Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1000}
    ])
    prices["Date"] = pd.to_datetime(prices["Date"])
    from src.data_loader import pivot_prices, pivot_volume
    price_df = pivot_prices(prices)
    volume_df = pivot_volume(prices)
    
    res = run_topdown_pipeline(
        price_df=price_df,
        volume_df=volume_df,
        dr_mapping_df=None,
        dr_price_df=None,
        dr_volume_df=None
    )
    # Check that fallback reports are empty or present as expected
    assert "dr_execution_quality_report" in res
    assert res["dr_execution_quality_report"].empty
