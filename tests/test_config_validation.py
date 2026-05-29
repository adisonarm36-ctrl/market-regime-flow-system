import pandas as pd

from src.config_validation import (
    DEMO_REFERENCE_MODE_WARNING,
    apply_demo_reference_mode,
    validate_data_sources_config,
    validate_country_universe,
    validate_dr_underlyings,
    validate_metadata_schema,
    validate_sector_mapping,
    validate_thresholds,
    validate_yahoo_source_config,
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


def test_validate_yahoo_source_config_missing_and_invalid_values():
    warnings = validate_yahoo_source_config(
        {
            "tickers": ["", " "],
            "interval": "1m",
            "cache_format": "json",
            "cache_dir": "",
            "cache_ttl_hours": -1,
            "fallback_to_cache": "yes",
            "start": "2026-01-02",
            "end": "2026-01-01",
            "reference_data": {},
        }
    )

    assert "Yahoo config missing tickers" in warnings[0]
    assert any("unsupported interval" in warning for warning in warnings)
    assert any("unsupported cache_format" in warning for warning in warnings)
    assert any("end date must be after start date" in warning for warning in warnings)


def test_validate_data_sources_config_checks_active_source_and_yahoo_settings():
    warnings = validate_data_sources_config(
        {
            "active_source": "missing",
            "source_settings": {
                "yahoo": {
                    "tickers": ["AAA"],
                    "period": "2y",
                    "interval": "1d",
                    "cache_dir": "data/cache/yahoo",
                    "cache_format": "csv",
                    "cache_ttl_hours": 8,
                    "fallback_to_cache": True,
                    "reference_data": {},
                }
            },
        }
    )

    assert any("active_source not found" in warning for warning in warnings)
    assert any("missing local metadata reference path" in warning for warning in warnings)


def test_demo_reference_mode_maps_missing_paths_without_mutating_config():
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "reference_data": {
                    "metadata_path": "data/reference/metadata.csv",
                    "sector_map_path": "data/reference/sector_map.csv",
                    "country_map_path": "data/reference/country_map.csv",
                }
            }
        },
    }

    result, warnings = apply_demo_reference_mode(config)

    reference_data = result["source_settings"]["yahoo"]["reference_data"]
    assert reference_data["metadata_path"] == "data/reference/metadata_sample.csv"
    assert reference_data["sector_map_path"] == "data/reference/sector_map_sample.csv"
    assert reference_data["country_map_path"] == "data/reference/country_map_sample.csv"
    assert config["source_settings"]["yahoo"]["reference_data"]["metadata_path"] == "data/reference/metadata.csv"
    assert DEMO_REFERENCE_MODE_WARNING in warnings
    assert any("metadata_path" in warning for warning in warnings)


def test_demo_reference_mode_preserves_existing_production_paths(tmp_path):
    metadata_path = tmp_path / "metadata.csv"
    metadata_path.write_text("Ticker,SecurityType,Country,Sector,Industry,Universe,Suspended\n", encoding="utf-8")
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "reference_data": {
                    "metadata_path": str(metadata_path),
                    "sector_map_path": "data/reference/sector_map.csv",
                }
            }
        },
    }

    result, warnings = apply_demo_reference_mode(config)

    reference_data = result["source_settings"]["yahoo"]["reference_data"]
    assert reference_data["metadata_path"] == str(metadata_path)
    assert reference_data["sector_map_path"] == "data/reference/sector_map_sample.csv"
    assert DEMO_REFERENCE_MODE_WARNING in warnings


def test_demo_reference_mode_replaces_empty_asset_map():
    config = {
        "active_source": "yahoo",
        "source_settings": {
            "yahoo": {
                "reference_data": {
                    "asset_map_path": "config/asset_map.yaml",
                }
            }
        },
    }

    result, warnings = apply_demo_reference_mode(config)

    assert result["source_settings"]["yahoo"]["reference_data"]["asset_map_path"] == "data/reference/asset_map_sample.csv"
    assert any("asset_map_path" in warning for warning in warnings)
