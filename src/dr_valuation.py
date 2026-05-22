from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import numpy as np


# Required columns definitions
REQUIRED_DR_MARKET_COLUMNS = ["Date", "DR_Ticker", "Open", "High", "Low", "Close", "Volume", "ValueTraded"]
REQUIRED_DR_BID_ASK_COLUMNS = ["Date", "DR_Ticker", "Bid", "Ask", "BidSize", "AskSize"]
REQUIRED_DR_FAIR_VALUE_COLUMNS = ["DR_Ticker", "UnderlyingTicker", "UnderlyingCurrency", "DR_Currency", "Ratio", "FXPair", "FeeAdjustmentPct", "RatioConvention"]
REQUIRED_FX_RATES_COLUMNS = ["Date", "FXPair", "Rate"]
REQUIRED_UNDERLYING_PRICES_COLUMNS = ["Date", "UnderlyingTicker", "Close", "Currency"]


# Data Loaders
def load_dr_market_data(path: str | Path) -> pd.DataFrame:
    """Load DR market data from CSV file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"DR market data path not found: {path}")
    df = pd.read_csv(path)
    errors = validate_dr_market_data_schema(df)
    if errors:
        raise ValueError("; ".join(errors))
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def load_dr_bid_ask_data(path: str | Path) -> pd.DataFrame:
    """Load DR bid-ask spread data from CSV file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"DR bid-ask data path not found: {path}")
    df = pd.read_csv(path)
    errors = validate_dr_bid_ask_schema(df)
    if errors:
        raise ValueError("; ".join(errors))
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def load_dr_fair_value_inputs(path: str | Path) -> pd.DataFrame:
    """Load DR fair value inputs mapping from CSV file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"DR fair value inputs path not found: {path}")
    df = pd.read_csv(path)
    errors = validate_dr_fair_value_inputs_schema(df)
    if errors:
        raise ValueError("; ".join(errors))
    return df


def load_fx_rates(path: str | Path) -> pd.DataFrame:
    """Load historical FX rates from CSV file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"FX rates path not found: {path}")
    df = pd.read_csv(path)
    errors = validate_fx_rates_schema(df)
    if errors:
        raise ValueError("; ".join(errors))
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def load_underlying_prices(path: str | Path) -> pd.DataFrame:
    """Load underlying asset prices from CSV file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Underlying prices path not found: {path}")
    df = pd.read_csv(path)
    errors = validate_underlying_prices_schema(df)
    if errors:
        raise ValueError("; ".join(errors))
    df["Date"] = pd.to_datetime(df["Date"])
    return df


# Schema Validators
def validate_dr_market_data_schema(df: pd.DataFrame) -> list[str]:
    """Validate schema of DR market data dataframe."""
    warnings: list[str] = []
    missing = [col for col in REQUIRED_DR_MARKET_COLUMNS if col not in df.columns]
    if missing:
        warnings.append(f"Missing DR market data columns: {', '.join(missing)}")
    return warnings


def validate_dr_bid_ask_schema(df: pd.DataFrame) -> list[str]:
    """Validate schema of DR bid-ask spread dataframe."""
    warnings: list[str] = []
    missing = [col for col in REQUIRED_DR_BID_ASK_COLUMNS if col not in df.columns]
    if missing:
        warnings.append(f"Missing DR bid-ask columns: {', '.join(missing)}")
    return warnings


def validate_dr_fair_value_inputs_schema(df: pd.DataFrame) -> list[str]:
    """Validate schema of DR fair value inputs mapping dataframe."""
    warnings: list[str] = []
    missing = [col for col in REQUIRED_DR_FAIR_VALUE_COLUMNS if col not in df.columns]
    if missing:
        warnings.append(f"Missing DR fair value mapping columns: {', '.join(missing)}")
    else:
        # Check for invalid ratio conventions
        invalid_convs = df[df["RatioConvention"] != "DR_per_Underlying"]["RatioConvention"].unique()
        if len(invalid_convs) > 0:
            warnings.append(f"Unsupported ratio conventions found: {', '.join(map(str, invalid_convs))}. Only 'DR_per_Underlying' is supported.")
    return warnings


def validate_fx_rates_schema(df: pd.DataFrame) -> list[str]:
    """Validate schema of FX rates dataframe."""
    warnings: list[str] = []
    missing = [col for col in REQUIRED_FX_RATES_COLUMNS if col not in df.columns]
    if missing:
        warnings.append(f"Missing FX rates columns: {', '.join(missing)}")
    return warnings


def validate_underlying_prices_schema(df: pd.DataFrame) -> list[str]:
    """Validate schema of underlying prices dataframe."""
    warnings: list[str] = []
    missing = [col for col in REQUIRED_UNDERLYING_PRICES_COLUMNS if col not in df.columns]
    if missing:
        warnings.append(f"Missing underlying prices columns: {', '.join(missing)}")
    return warnings


# Mathematical & Financial Calculations
def calculate_dr_fair_value(underlying_price: float, fx_rate: float, ratio: float, fee_adjustment_pct: float = 0) -> float:
    """Calculate DR fair value using ratio, exchange rate, and fee adjustments."""
    if ratio <= 0:
        raise ValueError("DR ratio must be greater than zero.")
    base_fv = (underlying_price * fx_rate) / ratio
    return base_fv * (1.0 - fee_adjustment_pct)


def calculate_premium_discount(dr_price: float, fair_value: float) -> float:
    """Calculate premium or discount percentage relative to fair value."""
    if pd.isna(fair_value) or fair_value <= 0:
        return np.nan
    return ((dr_price / fair_value) - 1.0) * 100.0


def calculate_bid_ask_spread_pct(bid: float, ask: float) -> float:
    """Calculate bid-ask spread as a percentage of the mid-price."""
    mid = (bid + ask) / 2.0
    if pd.isna(mid) or mid <= 0:
        return np.nan
    return ((ask - bid) / mid) * 100.0


def calculate_fx_adjusted_underlying_return(
    underlying_price_df: pd.DataFrame,
    fx_df: pd.DataFrame,
    ratio: float
) -> pd.DataFrame:
    """Calculate FX-adjusted prices and returns for the underlying ticker."""
    # Align by Date
    merged = pd.merge(underlying_price_df, fx_df, on="Date", suffixes=("_underlying", "_fx"))
    if merged.empty:
        return pd.DataFrame(columns=["Date", "fx_adjusted_price", "fx_adjusted_return"])
    
    # Calculate fx_adjusted_price
    merged["fx_adjusted_price"] = (merged["Close"] * merged["Rate"]) / ratio
    merged = merged.sort_values("Date").reset_index(drop=True)
    merged["fx_adjusted_return"] = merged["fx_adjusted_price"].pct_change()
    
    return merged[["Date", "fx_adjusted_price", "fx_adjusted_return"]]


def calculate_tracking_correlation(
    dr_price_df: pd.DataFrame,
    fx_adjusted_underlying_df: pd.DataFrame
) -> float:
    """Calculate correlation of daily returns between DR and FX-adjusted underlying."""
    # Calculate returns of DR
    dr_df = dr_price_df.sort_values("Date").copy()
    dr_df["dr_return"] = dr_df["Close"].pct_change()
    
    # Merge with underlying FX adjusted return by Date
    merged = pd.merge(dr_df[["Date", "dr_return"]], fx_adjusted_underlying_df[["Date", "fx_adjusted_return"]], on="Date").dropna()
    if len(merged) < 2 or merged["dr_return"].std() == 0 or merged["fx_adjusted_return"].std() == 0:
        return np.nan
        
    return float(merged["dr_return"].corr(merged["fx_adjusted_return"]))


def calculate_tracking_error(
    dr_return_df: pd.Series | pd.DataFrame,
    fx_adjusted_underlying_return_df: pd.Series | pd.DataFrame
) -> float:
    """Calculate tracking error as the daily standard deviation of return differences."""
    # Ensure they are aligned by date/index
    if isinstance(dr_return_df, pd.DataFrame) and "Date" in dr_return_df.columns:
        dr_return = dr_return_df.set_index("Date")["dr_return"] if "dr_return" in dr_return_df.columns else dr_return_df.set_index("Date").iloc[:, 0]
    else:
        dr_return = dr_return_df
        
    if isinstance(fx_adjusted_underlying_return_df, pd.DataFrame) and "Date" in fx_adjusted_underlying_return_df.columns:
        und_return = fx_adjusted_underlying_return_df.set_index("Date")["fx_adjusted_return"] if "fx_adjusted_return" in fx_adjusted_underlying_return_df.columns else fx_adjusted_underlying_return_df.set_index("Date").iloc[:, 0]
    else:
        und_return = fx_adjusted_underlying_return_df
        
    aligned = pd.concat([dr_return, und_return], axis=1).dropna()
    if len(aligned) < 2:
        return np.nan
        
    diff = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return float(diff.std() * 100.0)  # In percentage points
