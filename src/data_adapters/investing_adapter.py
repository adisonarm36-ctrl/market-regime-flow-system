from __future__ import annotations

from src.data_adapters.base import DataAdapter


class InvestingDataAdapter(DataAdapter):
    """Placeholder for a future Investing.com adapter."""

    def _not_implemented(self):
        raise NotImplementedError("Investing adapter is not implemented. Do not scrape websites; add a compliant provider implementation first.")

    load_prices = load_metadata = load_sector_map = load_dr_mapping = validate_schema = _not_implemented
