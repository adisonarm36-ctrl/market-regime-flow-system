import pandas as pd

from src.config_validation import (
    validate_country_universe,
    validate_dr_underlyings,
    validate_metadata_schema,
    validate_sector_mapping,
    validate_thresholds,
)


def test_validate_metadata_schema_missing_columns_and_unknown_type():
    missing = validate_metadata_schema(pd.DataFrame({"Ticker": ["DEMO"], "SecurityType": ["Stock"]}))
    unknown = validate_metadata_schema(
        pd.DataFrame(
            {
                "Ticker": ["DEMO"],
                "SecurityType": ["UnknownType"],
                "Country": ["Demo"],
                "Sector": ["Demo"],
                "Industry": ["Demo"],
                "Universe": ["Demo"],
                "Suspended": [False],
                "average_traded_value_20d": [1],
            }
        )
    )

    assert "Missing metadata columns" in missing[0]
    assert "Unknown security type" in unknown[0]


def test_validate_config_missing_sections():
    assert validate_country_universe({"countries": {"Thailand": []}})
    assert validate_sector_mapping({"sectors": {}, "industries": {}})
    assert validate_thresholds({}, "country_regime", ["bull"])


def test_validate_dr_underlyings_missing_and_unavailable():
    mapping = pd.DataFrame({"DR_Ticker": ["DEMO_DR"], "Underlying_Ticker": ["MISSING_UNDERLYING"]})

    warnings = validate_dr_underlyings(mapping, available_tickers={"DEMO_DR"})

    assert "DR underlying not found in prices" in warnings[0]
