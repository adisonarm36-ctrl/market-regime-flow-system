from __future__ import annotations

from src.data_adapters.base import DataAdapter
from src.data_adapters.csv_adapter import create_adapter_from_config
from src.data_adapters.investing_adapter import InvestingDataAdapter
from src.data_adapters.manual_upload_adapter import ManualUploadAdapter
from src.data_adapters.settrade_adapter import SettradeDataAdapter
from src.data_adapters.stooq_adapter import StooqDataAdapter
from src.data_adapters.yahoo_adapter import YahooDataAdapter


def get_data_adapter(config: dict) -> DataAdapter:
    """Select a data adapter from data_sources.yaml-style config."""
    active_source = config.get("active_source", "csv")
    source_settings = config.get("source_settings", {})
    if active_source == "csv":
        return create_adapter_from_config(source_settings.get("csv", {}))
    if active_source == "manual_upload":
        return ManualUploadAdapter()
    if active_source == "settrade":
        return SettradeDataAdapter()
    if active_source == "yahoo":
        return YahooDataAdapter.from_config(source_settings.get("yahoo", {}))
    if active_source == "stooq":
        return StooqDataAdapter()
    if active_source == "investing":
        return InvestingDataAdapter()
    raise ValueError(f"Unsupported data source: {active_source}")


def validate_data_source_config(config: dict) -> list[str]:
    """Validate active adapter settings and return warnings for optional data gaps."""
    warnings: list[str] = []
    active_source = config.get("active_source", "csv")
    source_settings = config.get("source_settings", {})
    if active_source == "yahoo":
        adapter = YahooDataAdapter.from_config(source_settings.get("yahoo", {}))
        warnings.extend(adapter.validate_schema())
    elif active_source == "csv":
        adapter = create_adapter_from_config(source_settings.get("csv", {}))
        warnings.extend(adapter.validate_schema())
    return warnings
