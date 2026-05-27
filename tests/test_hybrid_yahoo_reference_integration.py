import pandas as pd

from src.data_adapters.base import DataAdapter
from src.topdown_pipeline import run_pipeline_from_config


class MockYahooHybridAdapter(DataAdapter):
    def __init__(self, prices: pd.DataFrame, metadata_path: str | None = None, dr_mapping: pd.DataFrame | None = None) -> None:
        self.prices = prices
        self.metadata_path = metadata_path
        self.dr_mapping = dr_mapping
        self.warnings = ["mock yahoo historical prices loaded"]

    def load_prices(self) -> pd.DataFrame:
        return self.prices

    def load_metadata(self) -> pd.DataFrame:
        if self.metadata_path is None:
            return pd.DataFrame()
        return pd.read_csv(self.metadata_path)

    def load_sector_map(self) -> pd.DataFrame:
        return pd.DataFrame()

    def load_dr_mapping(self) -> pd.DataFrame:
        return self.dr_mapping if self.dr_mapping is not None else pd.DataFrame()

    def validate_schema(self) -> list[str]:
        return []


def _mock_prices(tickers: list[str]) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=70, freq="B")
    rows = []
    for ticker_index, ticker in enumerate(tickers):
        for i, day in enumerate(dates):
            close = 100 + ticker_index * 5 + i * (0.2 + ticker_index * 0.03)
            rows.append(
                {
                    "Date": day,
                    "Ticker": ticker,
                    "Open": close - 0.1,
                    "High": close + 0.4,
                    "Low": close - 0.4,
                    "Close": close,
                    "Volume": 1000 + i,
                    "Adjusted Close": close,
                }
            )
    return pd.DataFrame(rows)


def test_config_driven_pipeline_with_mocked_yahoo_and_local_metadata():
    prices = _mock_prices(["DEMO_US_EQUITY_ETF", "DEMO_US_BOND_ETF", "DEMO_TH_SAMPLE.BK", "DEMO_TH_DR"])
    dr_mapping = pd.DataFrame({"DR_Ticker": ["DEMO_TH_DR"], "Underlying_Ticker": ["DEMO_US_EQUITY_ETF"]})
    adapter = MockYahooHybridAdapter(prices, metadata_path="data/reference/metadata_sample.csv", dr_mapping=dr_mapping)

    outputs = run_pipeline_from_config(adapter=adapter)

    assert not outputs["global_flow_summary"].empty
    assert not outputs["country_breadth_summary"].empty
    assert not outputs["thailand_market_health"].empty
    assert not outputs["sector_breadth_summary"].empty
    assert not outputs["stock_ranking"].empty
    assert not outputs["dr_quality_ranking"].empty
    assert "warnings" in outputs
    assert "data_quality_report" in outputs
    assert "reference_data_report" in outputs


def test_pipeline_skips_sector_and_dr_when_reference_missing(tmp_path):
    prices = _mock_prices(["DEMO_US_EQUITY_ETF", "DEMO_MISSING"])
    adapter = MockYahooHybridAdapter(prices, metadata_path=None, dr_mapping=None)
    config_path = tmp_path / "data_sources.yaml"
    config_path.write_text(
        "active_source: yahoo\n"
        "source_settings:\n"
        "  yahoo:\n"
        "    tickers:\n"
        "      - DEMO_US_EQUITY_ETF\n"
        "      - DEMO_MISSING\n",
        encoding="utf-8",
    )

    outputs = run_pipeline_from_config(config_path=str(config_path), adapter=adapter)

    assert outputs["sector_breadth_summary"].empty
    assert "DR quality skipped" in outputs["dr_quality_ranking"]["data_quality_warning"].iloc[0]
    assert not outputs["warnings"].empty


def test_tickers_missing_metadata_are_flagged():
    prices = _mock_prices(["DEMO_US_EQUITY_ETF", "DEMO_NOT_IN_METADATA"])
    adapter = MockYahooHybridAdapter(prices, metadata_path="data/reference/metadata_sample.csv")

    outputs = run_pipeline_from_config(adapter=adapter)

    report = outputs["reference_data_report"]
    assert not report.loc[report["Ticker"].eq("DEMO_NOT_IN_METADATA"), "has_metadata"].iloc[0]
