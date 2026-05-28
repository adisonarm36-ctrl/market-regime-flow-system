from pathlib import Path

import pandas as pd

from src.dashboard import (
    CONFIG_SOURCE_MODE,
    MANUAL_FALLBACK_MODE,
    active_source_label,
    apply_demo_reference_runtime_config,
    apply_yahoo_runtime_options,
    apply_yahoo_ticker_universe,
    dashboard_source_options,
    disable_yahoo_force_refresh,
    yahoo_dependency_diagnostic,
    yahoo_cache_token,
    yahoo_cache_status,
)
from src.data_adapters.yahoo_adapter import YahooDataAdapter
from src.startup_diagnostics import (
    STREAMLIT_VENV_RUN_COMMAND,
    YFINANCE_INSTALL_COMMAND,
    build_production_reference_readiness,
    build_yahoo_startup_checklist,
    run_yahoo_historical_smoke_test,
    summarize_yahoo_smoke_test_state,
    summarize_yahoo_startup_state,
    startup_checklist_has_blockers,
    yfinance_missing_guidance,
)


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


def test_apply_demo_reference_runtime_config_requires_explicit_enable():
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "reference_data": {
                    "metadata_path": "data/reference/metadata.csv",
                }
            }
        },
    }

    disabled, disabled_warnings = apply_demo_reference_runtime_config(config, enabled=False)
    enabled, enabled_warnings = apply_demo_reference_runtime_config(config, enabled=True)

    assert disabled["source_settings"]["yahoo"]["reference_data"]["metadata_path"] == "data/reference/metadata.csv"
    assert disabled_warnings == []
    assert enabled["source_settings"]["yahoo"]["reference_data"]["metadata_path"] == "data/reference/metadata_sample.csv"
    assert any("fake/sample data" in warning for warning in enabled_warnings)
    assert config["source_settings"]["yahoo"]["reference_data"]["metadata_path"] == "data/reference/metadata.csv"


def test_yahoo_dependency_diagnostic_reports_available_with_mock():
    diagnostic = yahoo_dependency_diagnostic(find_spec=lambda package: object() if package == "yfinance" else None)

    assert diagnostic.importable is True
    assert diagnostic.package == "yfinance"
    assert diagnostic.fix_commands == ()


def test_yahoo_dependency_diagnostic_reports_missing_with_actionable_commands():
    diagnostic = yahoo_dependency_diagnostic(find_spec=lambda package: None)

    assert diagnostic.importable is False
    assert YFINANCE_INSTALL_COMMAND in diagnostic.fix_commands
    assert STREAMLIT_VENV_RUN_COMMAND in diagnostic.fix_commands
    guidance = yfinance_missing_guidance(diagnostic)
    assert "Yahoo historical loading is unavailable" in guidance
    assert YFINANCE_INSTALL_COMMAND in guidance
    assert STREAMLIT_VENV_RUN_COMMAND in guidance


def test_yahoo_startup_checklist_reports_healthy_config(tmp_path):
    metadata = tmp_path / "metadata.csv"
    sector = tmp_path / "sector.csv"
    country = tmp_path / "country.csv"
    for path in [metadata, sector, country]:
        path.write_text("Ticker,Value\n", encoding="utf-8")
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "tickers": ["AAA", "BBB"],
                "cache_dir": str(tmp_path / "cache"),
                "reference_data": {
                    "metadata_path": str(metadata),
                    "sector_map_path": str(sector),
                    "country_map_path": str(country),
                },
            }
        },
    }
    diagnostic = yahoo_dependency_diagnostic(find_spec=lambda package: object())
    cache_status = {
        "cache_path": str(tmp_path / "cache" / "prices.csv"),
        "cache_exists": True,
        "cache_is_stale": False,
    }

    rows = build_yahoo_startup_checklist(config, diagnostic, cache_status=cache_status)

    assert not startup_checklist_has_blockers(rows)
    assert any(row.item == "Configured Yahoo tickers" and row.status == "ok" for row in rows)
    assert any(row.item == "Required production references" and row.status == "ok" for row in rows)
    assert any(row.item == "Manual upload fallback" and row.status == "ok" for row in rows)


def test_yahoo_startup_checklist_blocks_missing_yfinance_and_tickers(tmp_path):
    config = {
        "active_source": "yahoo",
        "source_settings": {"yahoo": {"tickers": [], "cache_dir": str(tmp_path), "reference_data": {}}},
    }
    diagnostic = yahoo_dependency_diagnostic(find_spec=lambda package: None)

    rows = build_yahoo_startup_checklist(config, diagnostic)

    blockers = [row for row in rows if row.status == "blocker"]
    assert startup_checklist_has_blockers(rows)
    assert any(row.item == "Configured Yahoo tickers" for row in blockers)
    assert any(row.item == "yfinance availability" for row in blockers)
    assert any(row.item == "Yahoo data loading" for row in blockers)


def test_yahoo_startup_checklist_warns_for_demo_reference_mode():
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "tickers": ["AAA"],
                "cache_dir": "data/cache/yahoo",
                "reference_data": {
                    "metadata_path": "data/reference/metadata.csv",
                    "sector_map_path": "data/reference/sector_map.csv",
                    "country_map_path": "data/reference/country_map.csv",
                },
            }
        },
    }
    diagnostic = yahoo_dependency_diagnostic(find_spec=lambda package: object())

    rows = build_yahoo_startup_checklist(config, diagnostic, demo_reference_enabled=True)

    assert not startup_checklist_has_blockers(rows)
    assert any(row.item == "Required production references" and row.status == "warning" for row in rows)
    assert any(row.item == "Demo reference mode" and row.status == "warning" and "fake/sample" in row.detail for row in rows)


def test_demo_mode_missing_production_refs_is_demo_ready_not_blocked():
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "tickers": ["AAA"],
                "cache_dir": "data/cache/yahoo",
                "reference_data": {
                    "metadata_path": "data/reference/metadata.csv",
                    "sector_map_path": "data/reference/sector_map.csv",
                    "country_map_path": "data/reference/country_map.csv",
                },
            }
        },
    }
    diagnostic = yahoo_dependency_diagnostic(find_spec=lambda package: object())
    cache_status = {
        "cache_path": "data/cache/yahoo/demo.csv",
        "cache_exists": True,
        "cache_is_stale": False,
    }

    rows = build_yahoo_startup_checklist(
        config,
        diagnostic,
        cache_status=cache_status,
        demo_reference_enabled=True,
    )
    summary = summarize_yahoo_startup_state(rows, demo_reference_enabled=True)

    assert not startup_checklist_has_blockers(rows)
    assert summary.status == "demo_ready"
    assert summary.headline == "Ready for demo/smoke testing"
    assert summary.hard_blockers == ()
    assert summary.production_warnings
    assert summary.demo_warnings


def test_production_missing_refs_are_warnings_not_yahoo_runtime_blockers():
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "tickers": ["AAA"],
                "cache_dir": "data/cache/yahoo",
                "reference_data": {
                    "metadata_path": "data/reference/metadata.csv",
                    "sector_map_path": "data/reference/sector_map.csv",
                    "country_map_path": "data/reference/country_map.csv",
                },
            }
        },
    }
    diagnostic = yahoo_dependency_diagnostic(find_spec=lambda package: object())
    cache_status = {
        "cache_path": "data/cache/yahoo/demo.csv",
        "cache_exists": True,
        "cache_is_stale": False,
    }

    rows = build_yahoo_startup_checklist(config, diagnostic, cache_status=cache_status)
    summary = summarize_yahoo_startup_state(rows, demo_reference_enabled=False)

    assert not startup_checklist_has_blockers(rows)
    assert summary.status == "production_warning"
    assert "Not production-ready" in summary.headline
    assert summary.production_warnings


def test_yahoo_historical_smoke_test_summarizes_cache_first_success(tmp_path):
    class FakeYFinance:
        calls = 0

        def download(self, **kwargs):
            self.calls += 1
            return pd.DataFrame(
                {
                    "Open": [1.0, 2.0],
                    "High": [1.0, 2.0],
                    "Low": [1.0, 2.0],
                    "Close": [1.0, 2.0],
                    "Volume": [100, 200],
                },
                index=pd.to_datetime(["2026-01-01", "2026-01-02"]),
            )

    yf = FakeYFinance()
    adapter = YahooDataAdapter(["AAA"], cache_dir=tmp_path, cache_format="csv", yfinance_module=yf)

    first = run_yahoo_historical_smoke_test(adapter)
    second = run_yahoo_historical_smoke_test(adapter)

    assert first.attempted_tickers == ("AAA",)
    assert first.rows_loaded == 2
    assert first.start_date == "2026-01-01"
    assert first.end_date == "2026-01-02"
    assert first.cache_status == "cache_created"
    assert second.cache_exists_before is True
    assert yf.calls == 1


def test_yahoo_historical_smoke_test_reports_error_without_raising(tmp_path):
    class FakeYFinance:
        def download(self, **kwargs):
            raise RuntimeError("network disabled in test")

    adapter = YahooDataAdapter(["AAA"], cache_dir=tmp_path, cache_format="csv", yfinance_module=FakeYFinance())

    result = run_yahoo_historical_smoke_test(adapter)

    assert result.rows_loaded == 0
    assert "network disabled in test" in result.error
    assert result.cache_status == "cache_miss"

    summary = summarize_yahoo_smoke_test_state(result)

    assert summary.status == "blocked"
    assert summary.headline == "Blocked: Yahoo fetch failed and no cache is available"


def test_production_reference_readiness_flags_missing_columns(tmp_path):
    metadata = tmp_path / "metadata.csv"
    sector = tmp_path / "sector.csv"
    country = tmp_path / "country.csv"
    metadata.write_text("Ticker,SecurityType\nAAA,Stock\n", encoding="utf-8")
    sector.write_text("Ticker,Sector\nAAA,Demo\n", encoding="utf-8")
    country.write_text("Ticker,Country\nAAA,Demo\n", encoding="utf-8")
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "reference_data": {
                    "metadata_path": str(metadata),
                    "sector_map_path": str(sector),
                    "country_map_path": str(country),
                }
            }
        },
    }

    rows = build_production_reference_readiness(config)

    metadata_row = next(row for row in rows if row.reference == "Metadata")
    yahoo_row = next(row for row in rows if row.reference == "Metadata Yahoo ticker field")
    assert metadata_row.status == "invalid"
    assert "Country" in metadata_row.missing_columns
    assert yahoo_row.status == "warning"
    assert "will not infer" in yahoo_row.detail


def test_production_reference_readiness_detects_sample_files():
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "reference_data": {
                    "metadata_path": "data/reference/metadata_sample.csv",
                    "sector_map_path": "data/reference/sector_map_sample.csv",
                    "country_map_path": "data/reference/country_map_sample.csv",
                    "thailand_universe_path": "data/reference/thailand/thailand_universe_sample.csv",
                    "thailand_security_types_path": "data/reference/thailand/thailand_security_types_sample.csv",
                    "thailand_dr_mapping_path": "data/reference/thailand/thailand_dr_mapping_sample.csv",
                }
            }
        },
    }

    rows = build_production_reference_readiness(config)

    assert any(row.reference == "Metadata" and row.status == "sample" for row in rows)
    assert any(row.reference == "Thailand DR/DRx mapping" and row.status == "sample" for row in rows)
    assert any(row.reference == "Thailand Yahoo ticker field" and row.status == "warning" for row in rows)
