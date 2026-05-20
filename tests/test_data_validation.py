import pandas as pd

from src.data_validation import find_duplicate_rows, find_missing_data, validate_ohlcv


def test_validate_ohlcv_detects_missing_required_columns():
    df = pd.DataFrame({"Date": ["2026-01-01"], "Ticker": ["AAA"]})

    result = validate_ohlcv(df)

    assert not result.is_valid
    assert "Missing required columns" in result.errors[0]


def test_validate_ohlcv_detects_missing_and_duplicate_rows():
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-01"],
            "Ticker": ["AAA", "AAA"],
            "Open": [1.0, 1.0],
            "High": [1.0, 1.0],
            "Low": [1.0, 1.0],
            "Close": [None, 1.0],
            "Volume": [100, 100],
        }
    )

    result = validate_ohlcv(df)

    assert not result.is_valid
    assert len(find_missing_data(df)) == 1
    assert len(find_duplicate_rows(df)) == 2
