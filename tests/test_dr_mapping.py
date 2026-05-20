import pandas as pd
import pytest

from src.dr_mapping import attach_underlying_signal, validate_dr_mapping


def test_validate_dr_mapping_required_columns_and_duplicates():
    missing = validate_dr_mapping(pd.DataFrame({"DR_Ticker": ["AAA80"]}))
    duplicate = validate_dr_mapping(
        pd.DataFrame({"DR_Ticker": ["AAA80", "AAA80"], "Underlying_Ticker": ["AAA", "AAA"]})
    )

    assert "Missing required DR mapping columns" in missing[0]
    assert "Duplicate DR_Ticker" in duplicate[0]


def test_attach_underlying_signal_reports_missing_underlying():
    mapping = pd.DataFrame({"DR_Ticker": ["AAA80", "BBB80"], "Underlying_Ticker": ["AAA", "BBB"]})
    signal = pd.DataFrame({"Ticker": ["AAA"], "momentum_score": [80]})

    result = attach_underlying_signal(mapping, signal)

    assert result.loc[result["DR_Ticker"].eq("AAA80"), "signal_status"].iloc[0] == "available"
    assert result.loc[result["DR_Ticker"].eq("BBB80"), "signal_status"].iloc[0] == "missing_underlying_signal"
    assert pd.isna(result.loc[result["DR_Ticker"].eq("BBB80"), "momentum_score"].iloc[0])
