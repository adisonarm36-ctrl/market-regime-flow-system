import pandas as pd

from src.dr_quality import rank_dr_candidates_by_reference_quality
from src.topdown_pipeline import run_pipeline_from_config


class MockAdapter:
    warnings = []

    def __init__(self, prices):
        self.prices = prices

    def load_prices(self):
        return self.prices

    def load_metadata(self):
        return pd.DataFrame(
            {
                "Ticker": ["DEMO_TH_A", "DEMO_TH_B"],
                "SecurityType": ["Common Stock", "Common Stock"],
                "Country": ["Thailand", "Thailand"],
                "Sector": ["Demo", "Demo"],
                "Industry": ["Demo", "Demo"],
                "Universe": ["SET50", "SET100"],
                "Suspended": [False, False],
            }
        )

    def load_sector_map(self):
        return pd.DataFrame()

    def load_dr_mapping(self):
        return pd.DataFrame()


def _prices():
    dates = pd.date_range("2026-01-01", periods=80, freq="B")
    rows = []
    for ticker in ["DEMO_TH_A", "DEMO_TH_B", "DEMO_TH_DR"]:
        for i, date in enumerate(dates):
            rows.append(
                {
                    "Date": date,
                    "Ticker": ticker,
                    "Open": 10 + i,
                    "High": 11 + i,
                    "Low": 9 + i,
                    "Close": 10 + i,
                    "Volume": 1000,
                    "Adjusted Close": 10 + i,
                }
            )
    return pd.DataFrame(rows)


def test_dr_quality_ranking_works_with_mapping_only_and_liquidity_supported():
    mapping = pd.DataFrame(
        {
            "DR_Ticker": ["DR_A", "DRX_A"],
            "DR_Type": ["DR", "DRx"],
            "UnderlyingTicker": ["UNDER_A", "UNDER_A"],
            "IsActive": [True, True],
            "HasFairValueInput": [False, False],
        }
    )
    liquidity = pd.DataFrame({"Ticker": ["DR_A"], "average_traded_value_20d": [10_000_000], "average_volume_20d": [1000], "trading_days_ratio_60d": [1.0]})

    mapping_only = rank_dr_candidates_by_reference_quality(mapping)
    liquidity_supported = rank_dr_candidates_by_reference_quality(mapping, liquidity)

    assert set(mapping_only["quality_label"]) == {"Reference Only"}
    assert "Liquidity Supported" in liquidity_supported["quality_label"].tolist()


def test_pipeline_runs_when_thailand_reference_files_exist():
    outputs = run_pipeline_from_config(adapter=MockAdapter(_prices()))

    assert "thailand_reference_report" in outputs
    assert "thailand_eligibility_report" in outputs
    assert "thailand_dr_mapping_report" in outputs
    assert "dr_duplicate_underlying_report" in outputs


def test_pipeline_warns_but_does_not_crash_when_thailand_reference_files_missing(tmp_path):
    config = tmp_path / "data_sources.yaml"
    config.write_text(
        "\n".join(
            [
                "active_source: csv",
                "source_settings:",
                "  csv:",
                "    reference_data:",
                "      thailand_universe_path: missing/universe.csv",
                "      thailand_dr_mapping_path: missing/dr.csv",
            ]
        )
    )

    outputs = run_pipeline_from_config(config_path=str(config), adapter=MockAdapter(_prices()))

    warnings = "\n".join(outputs["warnings"]["warning"].astype(str).tolist())
    assert "thailand_universe_path skipped" in warnings
    assert "thailand_dr_mapping_path skipped" in warnings
