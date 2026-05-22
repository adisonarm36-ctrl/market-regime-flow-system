import pandas as pd

from src.thailand_breadth import filter_thailand_domestic_breadth_universe


def _metadata():
    return pd.DataFrame(
        {
            "Ticker": ["A", "B", "DR", "DRX", "ETF", "DW", "W", "SUSP", "MAI"],
            "Country": ["Thailand"] * 9,
            "SecurityType": ["Common Stock", "Common Stock", "DR", "DRx", "ETF", "DW", "Warrant", "Common Stock", "Common Stock"],
            "Universe": ["SET50", "SET100", "SET100", "SET100", "SET100", "SET100", "SET100", "SET100", "mai"],
            "IsDR": [False, False, True, False, False, False, False, False, False],
            "IsDRx": [False, False, False, True, False, False, False, False, False],
            "IsETF": [False, False, False, False, True, False, False, False, False],
            "IsDW": [False, False, False, False, False, True, False, False, False],
            "IsWarrant": [False, False, False, False, False, False, True, False, False],
            "Suspended": [False, False, False, False, False, False, False, True, False],
            "IncludeInDomesticBreadth": [True, True, False, False, False, False, False, False, True],
        }
    )


def test_excluded_security_types_and_suspended_are_not_domestic_breadth():
    result = filter_thailand_domestic_breadth_universe(_metadata(), universe="SET100")

    assert result["included_tickers"] == ["B"]
    excluded = result["excluded_tickers"].set_index("Ticker")["ExclusionReason"]
    assert "isdr" in excluded["DR"]
    assert "isdrx" in excluded["DRX"]
    assert "isetf" in excluded["ETF"]
    assert "isdw" in excluded["DW"]
    assert "iswarrant" in excluded["W"]
    assert "suspended" in excluded["SUSP"]


def test_liquidity_filter_excludes_illiquid_rows():
    liquidity = pd.DataFrame(
        {
            "Ticker": ["A", "B"],
            "average_traded_value_20d": [10_000_000, 1_000_000],
            "trading_days_ratio_60d": [0.95, 0.50],
        }
    )

    result = filter_thailand_domestic_breadth_universe(
        _metadata(),
        liquidity_df=liquidity,
        universe=None,
        min_avg_value_20d=5_000_000,
        min_trading_days_ratio_60d=0.85,
    )

    assert "A" in result["included_tickers"]
    assert "B" not in result["included_tickers"]
    excluded = result["excluded_tickers"].set_index("Ticker")["ExclusionReason"]
    assert "illiquid_avg_value_20d" in excluded["B"]


def test_set50_set100_and_mai_universe_filtering():
    metadata = _metadata()

    set50 = filter_thailand_domestic_breadth_universe(metadata, universe="SET50")
    set100 = filter_thailand_domestic_breadth_universe(metadata, universe="SET100")
    mai = filter_thailand_domestic_breadth_universe(metadata, universe="mai")

    assert set50["included_tickers"] == ["A"]
    assert set100["included_tickers"] == ["B"]
    assert mai["included_tickers"] == ["MAI"]
