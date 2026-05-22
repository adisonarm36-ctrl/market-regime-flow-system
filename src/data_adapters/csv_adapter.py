from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config_validation import REQUIRED_METADATA_COLUMNS, validate_metadata_schema
from src.data_adapters.base import DataAdapter
from src.data_validation import REQUIRED_OHLCV_COLUMNS, validate_ohlcv


class CsvDataAdapter(DataAdapter):
    """CSV-backed data adapter. This is the default V1 data source."""

    def __init__(
        self,
        price_path: str | Path | None = None,
        metadata_path: str | Path | None = None,
        sector_map_path: str | Path | None = None,
        dr_mapping_path: str | Path | None = None,
    ) -> None:
        self.price_path = Path(price_path) if price_path else None
        self.metadata_path = Path(metadata_path) if metadata_path else None
        self.sector_map_path = Path(sector_map_path) if sector_map_path else None
        self.dr_mapping_path = Path(dr_mapping_path) if dr_mapping_path else None

    def load_prices(self) -> pd.DataFrame:
        """Load OHLCV CSV data and validate required columns."""
        path = _require_path(self.price_path, "price_path")
        df = pd.read_csv(path)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
        result = validate_ohlcv(df)
        if not result.is_valid:
            raise ValueError("; ".join(result.errors))
        return df.sort_values(["Date", "Ticker"]).reset_index(drop=True)

    def load_metadata(self) -> pd.DataFrame:
        """Load metadata CSV data and validate metadata schema."""
        path = _require_path(self.metadata_path, "metadata_path")
        df = pd.read_csv(path)
        warnings = validate_metadata_schema(df)
        if warnings:
            raise ValueError("; ".join(warnings))
        return df

    def load_sector_map(self) -> pd.DataFrame:
        """Load sector or asset mapping CSV data."""
        path = _require_path(self.sector_map_path, "sector_map_path")
        return pd.read_csv(path)

    def load_dr_mapping(self) -> pd.DataFrame:
        """Load DR mapping CSV data."""
        path = _require_path(self.dr_mapping_path, "dr_mapping_path")
        df = pd.read_csv(path)
        missing = {"DR_Ticker", "Underlying_Ticker"}.difference(df.columns)
        if missing:
            raise ValueError(f"Missing DR mapping columns: {', '.join(sorted(missing))}")
        return df

    def validate_schema(self) -> list[str]:
        """Validate all configured CSV files that have paths."""
        warnings: list[str] = []
        if self.price_path:
            try:
                self.load_prices()
            except Exception as exc:
                warnings.append(f"prices: {exc}")
        else:
            warnings.append("price_path is not configured")

        if self.metadata_path:
            try:
                self.load_metadata()
            except Exception as exc:
                warnings.append(f"metadata: {exc}")
        else:
            warnings.append("metadata_path is not configured")

        if self.sector_map_path and not self.sector_map_path.exists():
            warnings.append(f"sector_map_path not found: {self.sector_map_path}")
        if self.dr_mapping_path:
            try:
                self.load_dr_mapping()
            except Exception as exc:
                warnings.append(f"dr_mapping: {exc}")
        return warnings


def create_adapter_from_config(settings: dict) -> CsvDataAdapter:
    """Create CsvDataAdapter from data_sources.yaml csv settings."""
    return CsvDataAdapter(
        price_path=settings.get("price_path"),
        metadata_path=settings.get("metadata_path"),
        sector_map_path=settings.get("sector_map_path"),
        dr_mapping_path=settings.get("dr_mapping_path"),
    )


def _require_path(path: Path | None, label: str) -> Path:
    if path is None:
        raise FileNotFoundError(f"{label} is not configured")
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path
