import numpy as np
import pandas as pd
import pytest

from src.dr_valuation import (
    calculate_dr_fair_value,
    calculate_premium_discount,
    calculate_bid_ask_spread_pct,
    calculate_fx_adjusted_underlying_return,
    calculate_tracking_correlation,
    calculate_tracking_error,
    validate_dr_fair_value_inputs_schema,
)


def test_fair_value_calculation_precision():
    # underlying = 150.0, fx_rate = 35.0, ratio = 10.0, fee_adjustment = 0.001 (0.1%)
    # expected base_fv = 150.0 * 35.0 / 10.0 = 525.0
    # expected fv after fee = 525.0 * (1 - 0.001) = 524.475
    fv = calculate_dr_fair_value(underlying_price=150.0, fx_rate=35.0, ratio=10.0, fee_adjustment_pct=0.001)
    assert pytest.approx(fv, rel=1e-5) == 524.475

    # Check that ratio <= 0 raises ValueError
    with pytest.raises(ValueError, match="DR ratio must be greater than zero."):
        calculate_dr_fair_value(underlying_price=150.0, fx_rate=35.0, ratio=0.0)


def test_premium_discount_sign_interpretation():
    # Test positive sign for DR trading above fair value (premium)
    # dr_price = 530.0, fair_value = 524.475
    # (530 / 524.475 - 1) * 100 = 1.0534%
    prem = calculate_premium_discount(dr_price=530.0, fair_value=524.475)
    assert prem > 0
    assert pytest.approx(prem, rel=1e-4) == 1.05343

    # Test negative sign for DR trading below fair value (discount)
    # dr_price = 520.0, fair_value = 524.475
    # (520 / 524.475 - 1) * 100 = -0.8532%
    disc = calculate_premium_discount(dr_price=520.0, fair_value=524.475)
    assert disc < 0
    assert pytest.approx(disc, rel=1e-4) == -0.85323

    # Handled correctly if fair value is NaN or <= 0
    assert np.isnan(calculate_premium_discount(dr_price=520.0, fair_value=np.nan))
    assert np.isnan(calculate_premium_discount(dr_price=520.0, fair_value=-5.0))
    assert np.isnan(calculate_premium_discount(dr_price=520.0, fair_value=0.0))


def test_ratio_convention_schema_validation():
    # Test valid RatioConvention column and values
    valid_df = pd.DataFrame([{
        "DR_Ticker": "DEMO_A",
        "UnderlyingTicker": "UND_A",
        "UnderlyingCurrency": "USD",
        "DR_Currency": "THB",
        "Ratio": 10.0,
        "FXPair": "USD/THB",
        "FeeAdjustmentPct": 0.001,
        "RatioConvention": "DR_per_Underlying"
    }])
    warnings = validate_dr_fair_value_inputs_schema(valid_df)
    assert len(warnings) == 0

    # Test missing RatioConvention column
    missing_df = valid_df.drop(columns=["RatioConvention"])
    warnings = validate_dr_fair_value_inputs_schema(missing_df)
    assert len(warnings) > 0
    assert "Missing DR fair value mapping columns" in warnings[0]

    # Test invalid RatioConvention values
    invalid_val_df = valid_df.copy()
    invalid_val_df.loc[0, "RatioConvention"] = "Underlying_per_DR"
    warnings = validate_dr_fair_value_inputs_schema(invalid_val_df)
    assert len(warnings) > 0
    assert "Unsupported ratio conventions found: Underlying_per_DR" in warnings[0]


def test_bid_ask_spread_pct():
    spread = calculate_bid_ask_spread_pct(bid=9.9, ask=10.1)
    # mid = 10.0, spread = 0.2 / 10.0 * 100 = 2.0%
    assert pytest.approx(spread) == 2.0
    assert np.isnan(calculate_bid_ask_spread_pct(bid=0, ask=0))


def test_fx_adjusted_underlying_return():
    und_price_df = pd.DataFrame([
        {"Date": "2026-05-20", "UnderlyingTicker": "U", "Close": 100.0, "Currency": "USD"},
        {"Date": "2026-05-21", "UnderlyingTicker": "U", "Close": 102.0, "Currency": "USD"},
    ])
    fx_df = pd.DataFrame([
        {"Date": "2026-05-20", "FXPair": "USD/THB", "Rate": 35.0},
        {"Date": "2026-05-21", "FXPair": "USD/THB", "Rate": 36.0},
    ])
    
    # ratio = 10.0
    # Day 1 price = 100.0 * 35.0 / 10.0 = 350.0
    # Day 2 price = 102.0 * 36.0 / 10.0 = 367.2
    # pct change = 367.2 / 350.0 - 1 = 4.914%
    res = calculate_fx_adjusted_underlying_return(und_price_df, fx_df, ratio=10.0)
    assert len(res) == 2
    assert res.loc[0, "fx_adjusted_price"] == 350.0
    assert res.loc[1, "fx_adjusted_price"] == 367.2
    assert pytest.approx(res.loc[1, "fx_adjusted_return"], rel=1e-4) == 0.04914
