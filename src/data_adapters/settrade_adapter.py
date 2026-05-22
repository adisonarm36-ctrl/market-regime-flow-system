from __future__ import annotations

from src.data_adapters.base import DataAdapter


class SettradeDataAdapter(DataAdapter):
    """Placeholder for a future Settrade adapter."""

    def _not_implemented(self):
        raise NotImplementedError("Settrade adapter is not implemented. Add a configured, permissioned data client before enabling this source.")

    load_prices = load_metadata = load_sector_map = load_dr_mapping = validate_schema = _not_implemented
