from pathlib import Path

import pandas as pd

from src.dashboard import (
    CONFIG_SOURCE_MODE,
    MANUAL_FALLBACK_MODE,
    active_source_label,
    apply_yahoo_runtime_options,
    apply_yahoo_ticker_universe,
    dashboard_source_options,
    disable_yahoo_force_refresh,
    yahoo_cache_token,
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
    assert status["cache_first_enabled"] is True


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
    assert status["cache_is_fresh"] is True
    assert yahoo_cache_token(adapter)


def test_apply_yahoo_runtime_options_does_not_mutate_config():
    config = {"source_settings": {"yahoo": {"fallback_to_cache": True}}}

    result = apply_yahoo_runtime_options(config, fallback_to_cache=False, force_refresh=True)

    assert result["source_settings"]["yahoo"]["fallback_to_cache"] is False
    assert result["source_settings"]["yahoo"]["force_refresh"] is True
    assert config["source_settings"]["yahoo"]["fallback_to_cache"] is True
    assert "force_refresh" not in config["source_settings"]["yahoo"]


def test_apply_yahoo_ticker_universe_does_not_mutate_config():
    config = {"source_settings": {"yahoo": {"tickers": ["OLD"]}}}

    result = apply_yahoo_ticker_universe(config, ["NEW"])

    assert result["source_settings"]["yahoo"]["tickers"] == ["NEW"]
    assert config["source_settings"]["yahoo"]["tickers"] == ["OLD"]


def test_disable_yahoo_force_refresh_does_not_mutate_config():
    config = {"source_settings": {"yahoo": {"fallback_to_cache": True, "force_refresh": True}}}

    result = disable_yahoo_force_refresh(config)

    assert result["source_settings"]["yahoo"]["force_refresh"] is False
    assert config["source_settings"]["yahoo"]["force_refresh"] is True
