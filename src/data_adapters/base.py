from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class DataAdapter(ABC):
    """Abstract interface for market data adapters."""

    @abstractmethod
    def load_prices(self) -> pd.DataFrame:
        """Load long-form OHLCV price data."""

    @abstractmethod
    def load_metadata(self) -> pd.DataFrame:
        """Load instrument metadata."""

    @abstractmethod
    def load_sector_map(self) -> pd.DataFrame:
        """Load sector or asset mapping data."""

    @abstractmethod
    def load_dr_mapping(self) -> pd.DataFrame:
        """Load DR-to-underlying mapping data."""

    @abstractmethod
    def validate_schema(self) -> list[str]:
        """Validate configured source schemas and return warnings/errors."""
