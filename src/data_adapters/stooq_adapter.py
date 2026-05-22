from __future__ import annotations

from src.data_adapters.base import DataAdapter


class StooqDataAdapter(DataAdapter):
    """Placeholder for a future Stooq adapter."""

    def _not_implemented(self):
        raise NotImplementedError("Stooq adapter is not implemented. Add an explicit provider module and tests before enabling live usage.")

    load_prices = load_metadata = load_sector_map = load_dr_mapping = validate_schema = _not_implemented
