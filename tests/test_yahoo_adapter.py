from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.data_adapters.factory import get_data_adapter
from src.data_adapters.yahoo_adapter import YahooDataAdapter


class FakeYFinance:
    def __init__(self, frame: pd.DataFrame | None = None, error: Exception | None = None) -> None:
        self.frame = frame
        self.error = error
        self.calls = 0

    def download(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.frame


def _single_ticker_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [99.0, 100.0],
            "High": [101.0, 102.0],
            "Low": [98.0, 99.0],
            "Close": [100.0, 101.0],
            "Volume": [1000, 1100],
        },
        index=pd.to_datetime(["2026-01-01", "2026-01-02"]),
    )


def _multi_ticker_frame() -> pd.DataFrame:
    dates = pd.to_datetime(["2026-01-01", "2026-01-02"])
    columns = pd.MultiIndex.from_product([["AAA", "BBB"], ["Open", "High", "Low", "Close", "Volume"]])
    return pd.DataFrame(
        [
            [10, 11, 9, 10.5, 100, 20, 21, 19, 20.5, 200],
            [11, 12, 10, 11.5, 110, 21, 22, 20, 21.5, 210],
        ],
        index=dates,
        columns=columns,
    )


def _field_first_multi_ticker_frame() -> pd.DataFrame:
    dates = pd.to_datetime(["2026-01-01", "2026-01-02"])
    columns = pd.MultiIndex.from_product([["Open", "High", "Low", "Close", "Volume", "Adj Close"], ["AAA", "BBB"]])
    return pd.DataFrame(
        [
            [10, 20, 11, 21, 9, 19, 10.5, 20.5, 100, 200, 10.4, 20.4],
            [11, 21, 12, 22, 10, 20, 11.5, 21.5, 110, 210, 11.4, 21.4],
        ],
        index=dates,
        columns=columns,
    )


def test_single_ticker_output_normalization(tmp_path):
    yf = FakeYFinance(_single_ticker_frame())
    adapter = YahooDataAdapter(["AAA"], cache_dir=tmp_path, cache_format="csv", yfinance_module=yf)

    result = adapter.load_prices()

    assert yf.calls == 1
    assert result.columns.tolist() == ["Date", "Ticker", "Open", "High", "Low", "Close", "Volume", "Adjusted Close"]
    assert result["Ticker"].unique().tolist() == ["AAA"]
    assert "missing adjusted close" in ";".join(adapter.warnings)


def test_multiindex_ticker_first_output_normalization(tmp_path):
    yf = FakeYFinance(_multi_ticker_frame())
    adapter = YahooDataAdapter(["AAA", "BBB"], cache_dir=tmp_path, cache_format="csv", yfinance_module=yf)

    result = adapter.load_prices()

    assert set(result["Ticker"]) == {"AAA", "BBB"}
    assert len(result) == 4


def test_multiindex_field_first_output_normalization(tmp_path):
    yf = FakeYFinance(_field_first_multi_ticker_frame())
    adapter = YahooDataAdapter(["AAA", "BBB"], cache_dir=tmp_path, cache_format="csv", yfinance_module=yf)

    result = adapter.load_prices()

    aaa = result[result["Ticker"].eq("AAA")].sort_values("Date")
    assert aaa["Adjusted Close"].iloc[-1] == 11.4


def test_cache_hit_avoids_yfinance_download(tmp_path):
    adapter = YahooDataAdapter(["AAA"], cache_dir=tmp_path, cache_format="csv", yfinance_module=FakeYFinance(_single_ticker_frame()))
    cache_path = adapter.cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cached = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01"]),
            "Ticker": ["AAA"],
            "Open": [1],
            "High": [1],
            "Low": [1],
            "Close": [1],
            "Volume": [1],
            "Adjusted Close": [1],
        }
    )
    cached.to_csv(cache_path, index=False)
    yf = FakeYFinance(_single_ticker_frame())
    adapter._yf = yf

    result = adapter.load_prices()

    assert yf.calls == 0
    assert result["Close"].iloc[0] == 1


def test_cache_stale_then_refresh(tmp_path):
    yf = FakeYFinance(_single_ticker_frame())
    adapter = YahooDataAdapter(["AAA"], cache_dir=tmp_path, cache_format="csv", cache_ttl_hours=0, yfinance_module=yf)
    cache_path = adapter.cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    _single_ticker_frame().reset_index(names="Date").assign(Ticker="AAA", **{"Adjusted Close": 100}).to_csv(cache_path, index=False)
    old_time = (datetime.now() - timedelta(days=2)).timestamp()
    os.utime(cache_path, (old_time, old_time))

    result = adapter.load_prices()

    assert yf.calls == 1
    assert result["Close"].iloc[-1] == 101.0


def test_fallback_to_stale_cache_on_fetch_failure(tmp_path):
    adapter = YahooDataAdapter(["AAA"], cache_dir=tmp_path, cache_format="csv", cache_ttl_hours=0, yfinance_module=FakeYFinance(error=RuntimeError("network down")))
    cache_path = adapter.cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cached = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01"]),
            "Ticker": ["AAA"],
            "Open": [1],
            "High": [1],
            "Low": [1],
            "Close": [1],
            "Volume": [1],
            "Adjusted Close": [1],
        }
    )
    cached.to_csv(cache_path, index=False)
    old_time = (datetime.now() - timedelta(days=2)).timestamp()
    os.utime(cache_path, (old_time, old_time))

    result = adapter.load_prices()

    assert result["Close"].iloc[0] == 1
    assert "fallback to stale cache" in adapter.warnings[0]


def test_missing_tickers_raises_value_error():
    with pytest.raises(ValueError, match="requires at least one ticker"):
        YahooDataAdapter([])


def test_unsupported_interval_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported Yahoo interval"):
        YahooDataAdapter(["AAA"], interval="1m")


def test_empty_yahoo_response_raises_clear_error(tmp_path):
    adapter = YahooDataAdapter(["AAA"], cache_dir=tmp_path, cache_format="csv", yfinance_module=FakeYFinance(pd.DataFrame()))

    with pytest.raises(RuntimeError, match="Yahoo historical data fetch failed"):
        adapter.load_prices()


def test_factory_returns_yahoo_adapter():
    adapter = get_data_adapter({"active_source": "yahoo", "source_settings": {"yahoo": {"tickers": ["AAA"]}}})

    assert isinstance(adapter, YahooDataAdapter)


def test_yahoo_adapter_loads_local_reference_data():
    adapter = YahooDataAdapter(
        ["DEMO_US_EQUITY_ETF"],
        reference_data={
            "metadata_path": "data/reference/metadata_sample.csv",
            "sector_map_path": "data/reference/sector_map_sample.csv",
            "dr_mapping_path": "data/sample/dr_mapping_sample.csv",
        },
    )

    metadata = adapter.load_metadata()
    sector = adapter.load_sector_map()
    dr_mapping = adapter.load_dr_mapping()

    assert "SecurityType" in metadata.columns
    assert "Sector" in sector.columns
    assert {"DR_Ticker", "Underlying_Ticker"}.issubset(dr_mapping.columns)


def test_yahoo_adapter_missing_optional_reference_data_warns():
    adapter = YahooDataAdapter(["AAA"], reference_data={"metadata_path": "data/reference/missing.csv"})

    metadata = adapter.load_metadata()
    warnings = adapter.validate_schema()

    assert metadata.empty
    assert "metadata path missing" in adapter.warnings[0]
    assert any("metadata path missing" in warning for warning in warnings)
