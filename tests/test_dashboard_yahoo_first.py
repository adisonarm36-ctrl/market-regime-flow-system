from pathlib import Path

import pandas as pd

from src.dashboard import (
    CONFIG_SOURCE_MODE,
    MANUAL_FALLBACK_MODE,
    active_source_label,
    dashboard_source_options,
    yahoo_cache_status,
)
from src.data_adapters.yahoo_adapter import YahooDataAdapter


def test_dashboard_source_options_default_to_config_source():
    options = dashboard_source_options()

    assert options[0] == CONFIG_SOURCE_MODE
    assert MANUAL_FALLBACK_MODE in options


def test_active_source_label_shows_config_value():
    assert active_source_label({"active_source": "yahoo"}) == "active_source: yahoo"
    assert active_source_label({}) == "active_source: unavailable"


def test_yahoo_cache_status_reports_missing_cache(tmp_path):
    adapter = YahooDataAdapter(["AAA"], cache_dir=tmp_path, cache_format="csv")

    status = yahoo_cache_status(adapter)

    assert status["cache_exists"] is False
    assert status["cache_path"].endswith(".csv")
    assert status["cache_last_updated"] == ""


def test_yahoo_cache_status_reports_last_updated(tmp_path):
    adapter = YahooDataAdapter(["AAA"], cache_dir=tmp_path, cache_format="csv")
    cache_path = adapter.cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "Date": [pd.Timestamp("2026-01-01")],
            "Ticker": ["AAA"],
            "Open": [1.0],
            "High": [1.0],
            "Low": [1.0],
            "Close": [1.0],
            "Volume": [100],
            "Adjusted Close": [1.0],
        }
    ).to_csv(Path(cache_path), index=False)

    status = yahoo_cache_status(adapter)

    assert status["cache_exists"] is True
    assert status["cache_last_updated"]
