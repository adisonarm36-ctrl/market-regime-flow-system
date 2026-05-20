import pandas as pd

from src.topdown_pipeline import run_topdown_pipeline


def test_run_topdown_pipeline_outputs_report_tables():
    dates = pd.date_range("2026-01-01", periods=260)
    price = pd.DataFrame({"AAA": range(100, 360), "BBB": range(360, 100, -1)}, index=dates, dtype=float)
    volume = pd.DataFrame({"AAA": [100] * 260, "BBB": [200] * 260}, index=dates, dtype=float)
    metadata = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB"],
            "Country": ["Thailand", "Thailand"],
            "Sector": ["Tech", "Energy"],
            "SecurityType": ["Stock", "Stock"],
        }
    )
    country_map = pd.DataFrame({"Ticker": ["AAA", "BBB"], "Country": ["Thailand", "Thailand"]})
    asset_map = pd.DataFrame({"Ticker": ["AAA", "BBB"], "asset_class": ["Equity", "Equity"]})

    outputs = run_topdown_pipeline(price, volume, metadata, asset_map, country_map)

    expected = {
        "global_flow_summary",
        "country_breadth_summary",
        "sector_breadth_summary",
        "cluster_summary",
        "stock_ranking",
        "dr_quality_ranking",
        "redundancy_report",
    }
    assert expected.issubset(outputs)
    assert not outputs["global_flow_summary"].empty
    assert not outputs["stock_ranking"].empty
