import pandas as pd
import pytest

from src.data_adapters import CsvDataAdapter, ManualUploadAdapter, get_data_adapter
from src.data_adapters.investing_adapter import InvestingDataAdapter
from src.data_adapters.settrade_adapter import SettradeDataAdapter
from src.data_adapters.stooq_adapter import StooqDataAdapter
from src.data_adapters.yahoo_adapter import YahooDataAdapter


def test_csv_adapter_loads_sample_files():
    adapter = CsvDataAdapter(
        price_path="data/sample/prices_sample.csv",
        metadata_path="data/sample/metadata_sample.csv",
        sector_map_path="data/sample/asset_map_sample.csv",
        dr_mapping_path="data/sample/dr_mapping_sample.csv",
    )

    prices = adapter.load_prices()
    metadata = adapter.load_metadata()
    sector_map = adapter.load_sector_map()
    dr_mapping = adapter.load_dr_mapping()

    assert {"Date", "Ticker", "Adjusted Close"}.issubset(prices.columns)
    assert "SecurityType" in metadata.columns
    assert "asset_class" in sector_map.columns
    assert dr_mapping["DR_Ticker"].iloc[0] == "DEMO_DR_ALPHA"
    assert adapter.validate_schema() == []


def test_csv_adapter_missing_file_handling():
    adapter = CsvDataAdapter(price_path="data/sample/missing.csv")

    with pytest.raises(FileNotFoundError):
        adapter.load_prices()

    assert "not found" in adapter.validate_schema()[0]


def test_csv_adapter_schema_validation(tmp_path):
    bad_prices = tmp_path / "bad_prices.csv"
    bad_prices.write_text("Date,Ticker,Close\n2026-01-01,DEMO,1\n", encoding="utf-8")
    adapter = CsvDataAdapter(price_path=bad_prices)

    with pytest.raises(ValueError, match="Missing required columns"):
        adapter.load_prices()


def test_manual_upload_adapter_validates_uploaded_frames():
    prices = pd.read_csv("data/sample/prices_sample.csv", parse_dates=["Date"])
    metadata = pd.read_csv("data/sample/metadata_sample.csv")
    adapter = ManualUploadAdapter(prices=prices, metadata=metadata)

    assert adapter.load_prices().equals(prices)
    assert adapter.validate_schema() == []


def test_adapter_selection_defaults_to_csv_and_supports_placeholders():
    csv_adapter = get_data_adapter({"active_source": "csv", "source_settings": {"csv": {"price_path": "data/sample/prices_sample.csv"}}})
    yahoo_adapter = get_data_adapter({"active_source": "yahoo", "source_settings": {"yahoo": {"tickers": ["DEMO"]}}})

    assert isinstance(csv_adapter, CsvDataAdapter)
    assert isinstance(yahoo_adapter, YahooDataAdapter)


@pytest.mark.parametrize(
    "adapter_cls",
    [SettradeDataAdapter, StooqDataAdapter, InvestingDataAdapter],
)
def test_provider_placeholders_raise_not_implemented(adapter_cls):
    adapter = adapter_cls()

    with pytest.raises(NotImplementedError):
        adapter.load_prices()
