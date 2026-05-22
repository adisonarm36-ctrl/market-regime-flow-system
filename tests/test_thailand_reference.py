import pandas as pd
import pytest

from src.thailand_reference import (
    load_thailand_universe,
    validate_thailand_universe_schema,
)


def test_thailand_universe_schema_validates_sample_file():
    df = load_thailand_universe("data/reference/thailand/thailand_universe_sample.csv")

    assert not df.empty
    assert str(df["IsDR"].dtype) == "boolean"
    assert "Ticker" in df.columns


def test_missing_required_thailand_universe_column_raises_clear_error():
    df = pd.DataFrame({"Ticker": ["DEMO_TH_A"]})

    with pytest.raises(ValueError, match="Missing required Thailand universe columns"):
        validate_thailand_universe_schema(df)


def test_boolean_normalization_accepts_common_local_reference_values(tmp_path):
    path = tmp_path / "universe.csv"
    path.write_text(
        "\n".join(
            [
                "Ticker,Name,Country,Exchange,Universe,SecurityType,Sector,Industry,Currency,IsDR,IsDRx,IsETF,IsDW,IsWarrant,Suspended,IncludeInDomesticBreadth,Notes",
                "DEMO_TH_A,Demo,Thailand,DEMO,SET50,Common Stock,Demo,Demo,THB,Y,N,0,1,false,TRUE,yes,Fake/demo",
            ]
        )
    )

    df = load_thailand_universe(path)

    assert bool(df["IsDR"].iloc[0])
    assert not bool(df["IsDRx"].iloc[0])
    assert bool(df["IsDW"].iloc[0])
    assert bool(df["IncludeInDomesticBreadth"].iloc[0])


def test_unknown_security_type_and_universe_are_flagged():
    df = pd.DataFrame(
        {
            "Ticker": ["DEMO_TH_A"],
            "Name": ["Demo"],
            "Country": ["Thailand"],
            "Exchange": ["DEMO"],
            "Universe": ["UNKNOWN_UNIVERSE"],
            "SecurityType": ["UNKNOWN_TYPE"],
            "Sector": ["Demo"],
            "Industry": ["Demo"],
            "Currency": ["THB"],
            "IsDR": [False],
            "IsDRx": [False],
            "IsETF": [False],
            "IsDW": [False],
            "IsWarrant": [False],
            "Suspended": [False],
            "IncludeInDomesticBreadth": [True],
            "Notes": ["Fake/demo"],
        }
    )

    warnings = validate_thailand_universe_schema(df)

    assert any("Unknown SecurityType" in warning for warning in warnings)
    assert any("Unknown Universe" in warning for warning in warnings)
