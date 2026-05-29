import pandas as pd
import pytest

from src.reference_data import (
    load_asset_map,
    load_dr_mapping,
    load_country_map,
    load_metadata,
    load_sector_map,
    merge_reference_data,
    validate_metadata_schema,
)


def test_load_metadata_csv_and_validate_schema():
    metadata = load_metadata("data/reference/metadata_sample.csv")

    assert {"Ticker", "SecurityType", "Country", "Sector", "Industry", "Universe", "Suspended"}.issubset(metadata.columns)
    assert "average_traded_value_20d" in metadata.columns


def test_demo_metadata_covers_default_yahoo_smoke_tickers():
    metadata = load_metadata("data/reference/metadata_sample.csv")
    required_tickers = {
        "SPY",
        "QQQ",
        "IWM",
        "TLT",
        "IEF",
        "SHY",
        "GLD",
        "SLV",
        "USO",
        "UUP",
        "BTC-USD",
        "ETH-USD",
    }

    assert required_tickers.issubset(set(metadata["Ticker"]))
    demo_rows = metadata[metadata["Ticker"].isin(required_tickers)]
    assert demo_rows["DemoData"].astype(str).str.lower().eq("true").all()


def test_demo_asset_map_covers_default_yahoo_smoke_tickers():
    asset_map = load_asset_map("data/reference/asset_map_sample.csv")
    required_tickers = {
        "SPY",
        "QQQ",
        "IWM",
        "TLT",
        "IEF",
        "SHY",
        "GLD",
        "SLV",
        "USO",
        "UUP",
        "BTC-USD",
        "ETH-USD",
    }

    assert {"Ticker", "asset_class"}.issubset(asset_map.columns)
    assert required_tickers.issubset(set(asset_map["Ticker"]))


def test_missing_required_metadata_columns_raises_clear_error():
    bad = pd.DataFrame({"Ticker": ["DEMO_ONLY"]})

    with pytest.raises(ValueError, match="Missing required metadata columns"):
        validate_metadata_schema(bad)


def test_load_sector_and_country_maps():
    sector = load_sector_map("data/reference/sector_map_sample.csv")
    country = load_country_map("data/reference/country_map_sample.csv")

    assert {"Ticker", "Sector"}.issubset(sector.columns)
    assert {"Ticker", "Country"}.issubset(country.columns)


def test_merge_reference_data_flags_missing_metadata():
    price_df = pd.DataFrame(
        {
            "DEMO_US_EQUITY_ETF": [1.0, 2.0],
            "DEMO_MISSING": [1.0, 1.5],
        },
        index=pd.date_range("2026-01-01", periods=2),
    )
    metadata = load_metadata("data/reference/metadata_sample.csv")

    merged, warnings = merge_reference_data(price_df, metadata)

    assert merged.loc[merged["Ticker"].eq("DEMO_MISSING"), "missing_metadata"].iloc[0]
    assert "tickers missing metadata" in warnings[0]


def test_load_dr_mapping_accepts_supported_alias_columns(tmp_path):
    path = tmp_path / "dr_mapping.csv"
    path.write_text("DRTicker,UnderlyingTicker\nDEMO_DR,DEMO_UNDERLYING\n", encoding="utf-8")

    result = load_dr_mapping(path)

    assert result["DR_Ticker"].tolist() == ["DEMO_DR"]
    assert result["Underlying_Ticker"].tolist() == ["DEMO_UNDERLYING"]
    assert result["UnderlyingTicker"].tolist() == ["DEMO_UNDERLYING"]
