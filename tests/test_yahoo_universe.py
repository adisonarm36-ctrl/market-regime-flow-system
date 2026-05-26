import pandas as pd

from src.yahoo_universe import (
    build_thailand_domestic_yahoo_ticker_universe,
    build_yahoo_ticker_universe,
    find_yahoo_ticker_column,
)


def test_build_yahoo_ticker_universe_uses_only_local_reference_values():
    reference = pd.DataFrame(
        {
            "Ticker": ["LOCAL_A", "LOCAL_B", "LOCAL_C"],
            "Universe": ["Demo", "Demo", "Other"],
            "YahooTicker": ["AAA.BK", "", "CCC.BK"],
        }
    )

    result = build_yahoo_ticker_universe(reference, universe="Demo")

    assert result.yahoo_tickers == ["AAA.BK"]
    assert "LOCAL_B" in result.warnings[0]


def test_build_yahoo_ticker_universe_warns_when_format_column_missing():
    reference = pd.DataFrame({"Ticker": ["LOCAL_A"], "Universe": ["Demo"]})

    result = build_yahoo_ticker_universe(reference, universe="Demo")

    assert result.yahoo_tickers == []
    assert "Yahoo ticker format missing" in result.warnings[0]


def test_find_yahoo_ticker_column_supports_known_local_field_names():
    assert find_yahoo_ticker_column(pd.DataFrame({"Yahoo_Symbol": ["AAA"]})) == "Yahoo_Symbol"


def test_thailand_domestic_yahoo_universe_preserves_exclusion_rules():
    metadata = pd.DataFrame(
        {
            "Ticker": ["A", "B", "DR", "ETF", "SUSP"],
            "Country": ["Thailand"] * 5,
            "SecurityType": ["Common Stock", "Common Stock", "DR", "ETF", "Common Stock"],
            "Universe": ["SET100"] * 5,
            "IsDR": [False, False, True, False, False],
            "IsDRx": [False] * 5,
            "IsETF": [False, False, False, True, False],
            "IsDW": [False] * 5,
            "IsWarrant": [False] * 5,
            "Suspended": [False, False, False, False, True],
            "IncludeInDomesticBreadth": [True, True, False, False, False],
            "YahooTicker": ["A.BK", "", "DR.BK", "ETF.BK", "SUSP.BK"],
        }
    )

    result = build_thailand_domestic_yahoo_ticker_universe(metadata, universe="SET100")

    assert result.yahoo_tickers == ["A.BK"]
    assert any("B" in warning for warning in result.warnings)
    assert any("excluded 3" in warning for warning in result.warnings)
