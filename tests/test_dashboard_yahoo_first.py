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
    build_demo_run_summary,
    build_signal_card_rows,
    build_signal_detail_sections,
    build_signal_filter_options,
    build_today_decision_hub_tables,
    filter_signal_ranking,
    should_enable_demo_reference_by_default,
    summarize_dashboard_warnings,
    yahoo_dependency_diagnostic,
    yahoo_cache_token,
    yahoo_cache_status,
)
from src.data_adapters.yahoo_adapter import YahooDataAdapter
from src.config_validation import apply_demo_reference_mode
from src.topdown_pipeline import run_pipeline_from_config
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


def test_first_run_missing_production_refs_defaults_to_demo_mode():
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "reference_data": {
                    "metadata_path": "data/reference/metadata.csv",
                    "sector_map_path": "data/reference/sector_map.csv",
                    "country_map_path": "data/reference/country_map.csv",
                    "asset_map_path": "config/asset_map.yaml",
                }
            }
        },
    }

    assert should_enable_demo_reference_by_default(config) is True


def test_first_run_demo_default_stays_off_when_production_refs_exist(tmp_path):
    metadata = tmp_path / "metadata.csv"
    sector = tmp_path / "sector.csv"
    country = tmp_path / "country.csv"
    metadata.write_text("Ticker,SecurityType,Country,Sector,Industry,Universe,Suspended\n", encoding="utf-8")
    sector.write_text("Ticker,Sector\n", encoding="utf-8")
    country.write_text("Ticker,Country\n", encoding="utf-8")
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

    assert should_enable_demo_reference_by_default(config) is False


def test_demo_reference_runtime_config_maps_empty_asset_map_to_sample():
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "reference_data": {
                    "metadata_path": "data/reference/metadata.csv",
                    "sector_map_path": "data/reference/sector_map.csv",
                    "country_map_path": "data/reference/country_map.csv",
                    "asset_map_path": "config/asset_map.yaml",
                }
            }
        },
    }

    enabled, warnings = apply_demo_reference_runtime_config(config, enabled=True)
    reference_data = enabled["source_settings"]["yahoo"]["reference_data"]

    assert reference_data["asset_map_path"] == "data/reference/asset_map_sample.csv"
    assert any("asset_map_path" in warning for warning in warnings)


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


def test_demo_mode_pipeline_outputs_global_and_asset_flow_with_default_yahoo_tickers():
    tickers = [
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
    ]
    dates = pd.date_range("2026-01-01", periods=70)
    rows = []
    for ticker_index, ticker in enumerate(tickers):
        for day_index, date in enumerate(dates):
            close = 100.0 + ticker_index + day_index * (1 + ticker_index / 20)
            rows.append(
                {
                    "Date": date,
                    "Ticker": ticker,
                    "Open": close,
                    "High": close + 1,
                    "Low": close - 1,
                    "Close": close,
                    "Volume": 1000 + ticker_index,
                    "Adjusted Close": close,
                }
            )

    class FakeYahooAdapter:
        warnings: list[str] = []

        def load_prices(self):
            return pd.DataFrame(rows)

    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "tickers": tickers,
                "reference_data": {
                    "metadata_path": "data/reference/metadata.csv",
                    "sector_map_path": "data/reference/sector_map.csv",
                    "country_map_path": "data/reference/country_map.csv",
                    "asset_map_path": "config/asset_map.yaml",
                    "dr_mapping_path": "config/dr_mapping.yaml",
                },
            }
        },
    }
    runtime_config, _ = apply_demo_reference_mode(config)

    outputs = run_pipeline_from_config(runtime_config, adapter=FakeYahooAdapter())
    warnings = "\n".join(outputs["warnings"]["warning"].astype(str).tolist())

    assert not outputs["global_flow_summary"].empty
    assert not outputs["asset_class_flow_summary"].empty
    assert set(outputs["global_flow_summary"]["Ticker"]) == set(tickers)
    assert outputs["data_quality_report"]["metadata_coverage_pct"].iloc[0] == 100
    assert "Missing metadata columns" not in warnings
    assert "tickers missing metadata" not in warnings

    readiness_rows = build_production_reference_readiness(config)
    summary = build_demo_run_summary(outputs, demo_reference_enabled=True, production_readiness_rows=readiness_rows)
    assert summary["global_flow_rows"].iloc[0] > 0
    assert summary["asset_class_flow_rows"].iloc[0] > 0
    assert summary["metadata_coverage"].iloc[0] == "100.0%"
    assert "not production-ready" in summary["production_readiness_status"].iloc[0]


def test_dashboard_warning_summary_collapses_adjusted_close_warnings():
    grouped = summarize_dashboard_warnings(
        [
            "missing adjusted close for SPY; using Close as Adjusted Close",
            "missing adjusted close for QQQ; using Close as Adjusted Close",
            "metadata_path skipped: reference path not found",
        ]
    )

    optional = "\n".join(grouped["Optional skipped layers"])
    assert "2 ticker(s) missing adjusted close" in optional
    assert "SPY, QQQ" in optional


def test_today_decision_hub_uses_existing_outputs_without_new_scores():
    outputs = {
        "global_flow_summary": pd.DataFrame({"Ticker": ["SPY"], "flow_score": [88.2], "flow_classification": ["Strong Inflow"]}),
        "country_breadth_summary": pd.DataFrame({"country": ["Thailand"], "breadth_score": [66.0], "regime": ["Bull"]}),
        "thailand_market_health": pd.DataFrame({"universe": ["SET ex-DR"], "breadth_score": [64.0], "regime": ["Bull"]}),
        "sector_breadth_summary": pd.DataFrame({"Sector": ["Tech"], "breadth_score": [75.0], "regime": ["Strong Bull"]}),
        "stock_ranking": pd.DataFrame(
            {
                "Ticker": ["AAA", "BBB"],
                "research_score": [82.0, 75.0],
                "signal_type": ["research signal only", "research signal only"],
                "Country": ["Thailand", "Thailand"],
                "Sector": ["Tech", None],
                "reason": ["momentum score available", ""],
                "failed_filters": ["", "low liquidity"],
                "data_quality_warning": ["", "missing sector"],
            }
        ),
        "warnings": pd.DataFrame({"warning": ["metadata_path skipped: reference path not found"]}),
        "backtest_warnings": pd.DataFrame({"warning": ["historical research assumptions only, not financial advice"]}),
    }

    tables = build_today_decision_hub_tables(
        outputs,
        source_label="active_source: yahoo",
        demo_reference_enabled=True,
        cache_status={"cache_exists": True, "cache_path": "data/cache/yahoo/demo.parquet", "cache_is_stale": False, "cache_last_updated": "2026-05-29"},
    )

    assert set(tables) == {"Market Regime", "Top Signals", "Risk Alerts", "Strategy Health", "Data Freshness", "Quick Actions"}
    assert tables["Market Regime"]["source"].tolist() == [
        "country_breadth_summary",
        "thailand_market_health",
        "global_flow_summary",
        "sector_breadth_summary",
    ]
    assert tables["Top Signals"]["Ticker"].tolist() == ["AAA", "BBB"]
    assert tables["Top Signals"].loc[1, "sector"] == "Not available"
    assert "low liquidity" in tables["Top Signals"].loc[1, "warnings"]
    assert not any("buy" in " ".join(table.astype(str).stack().tolist()).lower() for table in tables.values())
    assert any("fake/sample-only" in detail for detail in tables["Data Freshness"]["detail"].astype(str))
    assert any(tables["Risk Alerts"]["category"].eq("Backtest"))


def test_today_decision_hub_empty_outputs_are_explicitly_empty():
    tables = build_today_decision_hub_tables({}, source_label="", demo_reference_enabled=False)

    assert tables["Market Regime"].empty
    assert tables["Top Signals"].empty
    assert tables["Risk Alerts"].empty
    assert tables["Strategy Health"]["status"].eq("skipped").all()
    assert "Not available" in tables["Data Freshness"]["detail"].tolist()
    assert tables["Quick Actions"]["status"].tolist() == ["missing", "ok", "missing"]


def test_signal_filter_options_use_existing_stock_ranking_fields():
    ranking = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB", "DR1"],
            "SecurityType": ["Stock", "Stock", "DR"],
            "Country": ["Thailand", "United States", "Thailand"],
            "Sector": ["Tech", "Health", ""],
            "signal_type": ["research signal only", "research signal only", "research signal only"],
            "failed_filters": ["", "low liquidity", ""],
            "data_quality_warning": ["", "", "missing_spread"],
        }
    )

    options = build_signal_filter_options(ranking)

    assert options["countries"] == ["Thailand", "United States"]
    assert options["sectors"] == ["Health", "Tech"]
    assert options["signal_types"] == ["research signal only"]
    assert options["data_quality"] == ["No warnings reported", "Warnings reported"]
    assert options["failed_filter_states"] == ["Failed filters", "No failed filters"]


def test_filter_signal_ranking_preserves_source_rows_and_sorting():
    ranking = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB", "CCC"],
            "Country": ["Thailand", "Thailand", "United States"],
            "Sector": ["Tech", "Health", "Tech"],
            "signal_type": ["research signal only", "research signal only", "research signal only"],
            "research_score": [70.0, 90.0, 80.0],
            "failed_filters": ["", "low liquidity", ""],
            "data_quality_warning": ["", "missing metadata", ""],
        }
    )

    filtered = filter_signal_ranking(
        ranking,
        countries=["Thailand"],
        data_quality=["Warnings reported"],
        failed_filter_states=["Failed filters"],
        sort_by="research_score",
    )

    assert filtered["Ticker"].tolist() == ["BBB"]
    assert ranking["Ticker"].tolist() == ["AAA", "BBB", "CCC"]

    sorted_all = filter_signal_ranking(ranking, sort_by="research_score")
    assert sorted_all["Ticker"].tolist() == ["BBB", "CCC", "AAA"]


def test_signal_card_rows_render_badges_and_missing_fields_without_invention():
    ranking = pd.DataFrame(
        {
            "Ticker": ["DR1", "AAA"],
            "SecurityType": ["DR", "Stock"],
            "Country": ["Thailand", None],
            "Sector": ["", "Tech"],
            "Industry": [None, "Software"],
            "research_score": [88.0, None],
            "momentum_score": [77.0, 66.0],
            "trend_quality": ["above 50ma", ""],
            "signal_type": ["research signal only", "research signal only"],
            "reason": ["DR quality available", ""],
            "failed_filters": ["", "failed liquidity"],
            "data_quality_warning": ["missing_spread", ""],
        }
    )

    cards = build_signal_card_rows(ranking)

    assert cards.loc[0, "score"] == "88.00"
    assert "[Warning] DR/DRx proxy" in cards.loc[0, "badges"]
    assert "[Warning] Low data confidence" in cards.loc[0, "badges"]
    assert cards.loc[0, "sector"] == "Not available"
    assert cards.loc[1, "country"] == "Not available"
    assert cards.loc[1, "score"] == "Not available"
    assert "[Warning] Failed filters" in cards.loc[1, "badges"]


def test_signal_detail_sections_split_fact_assumption_warning_and_quality():
    row = pd.Series(
        {
            "Ticker": "AAA",
            "SecurityType": "Stock",
            "Country": "Thailand",
            "Sector": "Tech",
            "Industry": "Software",
            "research_score": 88.0,
            "momentum_score": 72.5,
            "reason": "momentum score available",
            "signal_type": "research signal only",
            "failed_filters": "",
            "data_quality_warning": "",
        }
    )

    sections = build_signal_detail_sections(row)

    assert set(sections) == {"Facts", "Assumptions", "Warnings", "Data Quality", "Supporting Row"}
    facts = sections["Facts"]
    assert facts.loc[facts["item"].eq("Ticker"), "value"].iloc[0] == "AAA"
    assert facts.loc[facts["item"].eq("Research score"), "value"].iloc[0] == "88.0"
    assumptions = "\n".join(sections["Assumptions"]["value"].astype(str).tolist())
    assert "Existing stock_ranking output" in assumptions
    assert "Needs data source" in assumptions
    assert sections["Warnings"].empty
    assert sections["Data Quality"].loc[sections["Data Quality"]["item"].eq("Sector metadata"), "value"].iloc[0] == "available"


def test_signal_detail_sections_preserve_dr_boundary_and_missing_metadata():
    row = pd.Series(
        {
            "Ticker": "DR1",
            "SecurityType": "DR",
            "Country": "Thailand",
            "Sector": None,
            "Industry": None,
            "research_score": 80.0,
            "dr_quality_score": 65.0,
            "reason": "",
            "signal_type": "research signal only",
            "failed_filters": "low liquidity",
            "dr_data_quality_warning": "missing_spread",
        }
    )

    sections = build_signal_detail_sections(row)

    warnings = "\n".join(sections["Warnings"].astype(str).stack().tolist())
    assert "DR/DRx proxy" in warnings
    assert "Do not use DR/DRx rows to judge Thailand domestic breadth" in warnings
    assert "low liquidity" in warnings
    assert "missing_spread" in warnings
    quality = sections["Data Quality"]
    assert quality.loc[quality["item"].eq("Sector metadata"), "value"].iloc[0] == "Needs data source"
    assert quality.loc[quality["item"].eq("Industry metadata"), "value"].iloc[0] == "Needs data source"
    supporting = sections["Supporting Row"]
    assert "DR1" in supporting["value"].tolist()
