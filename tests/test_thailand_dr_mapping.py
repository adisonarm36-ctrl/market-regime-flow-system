import pandas as pd
import pytest

from src.dr_mapping import (
    get_dr_candidates_for_underlying,
    group_drs_by_underlying,
    identify_duplicate_dr_underlyings,
    validate_dr_mapping_schema,
)


def _mapping():
    return pd.DataFrame(
        {
            "DR_Ticker": ["DR_A", "DRX_A", "DR_B"],
            "DR_Type": ["DR", "DRx", "DR"],
            "UnderlyingTicker": ["UNDER_A", "UNDER_A", "UNDER_B"],
            "UnderlyingExchange": ["DEMO", "DEMO", "DEMO"],
            "UnderlyingCountry": ["United States", "United States", "Japan"],
            "UnderlyingCurrency": ["USD", "USD", "JPY"],
            "DR_Currency": ["THB", "THB", "THB"],
            "Ratio": [1.0, 0.5, 1.0],
            "IssuerCode": ["ISS", "ISS", "ISS"],
            "IsActive": ["Y", "Y", "N"],
        }
    )


def test_thailand_dr_mapping_schema_validates():
    warnings = validate_dr_mapping_schema(_mapping())

    assert any("Optional DR fair value field missing" in warning for warning in warnings)


def test_missing_underlying_ticker_raises_validation_error():
    mapping = _mapping()
    mapping.loc[0, "UnderlyingTicker"] = ""

    with pytest.raises(ValueError, match="Missing underlying ticker"):
        validate_dr_mapping_schema(mapping)


def test_duplicate_underlying_groups_and_candidates_are_identified():
    mapping = _mapping()

    groups = group_drs_by_underlying(mapping)
    candidates = get_dr_candidates_for_underlying(mapping, "UNDER_A")
    duplicates = identify_duplicate_dr_underlyings(mapping)

    assert set(groups) == {"UNDER_A", "UNDER_B"}
    assert candidates["DR_Ticker"].tolist() == ["DR_A", "DRX_A"]
    assert duplicates.loc[0, "UnderlyingTicker"] == "UNDER_A"
