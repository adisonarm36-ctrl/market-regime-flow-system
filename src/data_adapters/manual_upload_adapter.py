from __future__ import annotations

import pandas as pd

from src.config_validation import validate_metadata_schema
from src.data_adapters.base import DataAdapter
from src.data_validation import validate_ohlcv


class ManualUploadAdapter(DataAdapter):
    """Adapter for already-uploaded Streamlit CSV dataframes."""

    def __init__(
        self,
        prices: pd.DataFrame | None = None,
        metadata: pd.DataFrame | None = None,
        sector_map: pd.DataFrame | None = None,
        dr_mapping: pd.DataFrame | None = None,
    ) -> None:
        self.prices = prices
        self.metadata = metadata
        self.sector_map = sector_map
        self.dr_mapping = dr_mapping

    def load_prices(self) -> pd.DataFrame:
        """Return uploaded OHLCV data."""
        if self.prices is None:
            raise FileNotFoundError("Manual upload prices are missing")
        return self.prices.copy()

    def load_metadata(self) -> pd.DataFrame:
        """Return uploaded metadata."""
        if self.metadata is None:
            raise FileNotFoundError("Manual upload metadata is missing")
        return self.metadata.copy()

    def load_sector_map(self) -> pd.DataFrame:
        """Return uploaded sector map."""
        if self.sector_map is None:
            raise FileNotFoundError("Manual upload sector map is missing")
        return self.sector_map.copy()

    def load_dr_mapping(self) -> pd.DataFrame:
        """Return uploaded DR mapping."""
        if self.dr_mapping is None:
            raise FileNotFoundError("Manual upload DR mapping is missing")
        return self.dr_mapping.copy()

    def validate_schema(self) -> list[str]:
        """Validate uploaded dataframes that are present."""
        warnings: list[str] = []
        if self.prices is None:
            warnings.append("manual upload prices are missing")
        else:
            result = validate_ohlcv(self.prices)
            warnings.extend(result.errors)
        if self.metadata is not None:
            warnings.extend(validate_metadata_schema(self.metadata))
        return warnings
