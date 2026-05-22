import pandas as pd

from src.config_loader import load_yaml
from src.data_loader import pivot_prices, pivot_volume
from src.report_generator import build_daily_report, export_report_to_csv, export_report_to_html
from src.topdown_pipeline import run_topdown_pipeline


def test_sample_data_runs_full_pipeline_and_exports(tmp_path):
    prices = pd.read_csv("data/sample/prices_sample.csv", parse_dates=["Date"])
    metadata = pd.read_csv("data/sample/metadata_sample.csv")
    asset_map = pd.read_csv("data/sample/asset_map_sample.csv")
    dr_mapping = pd.DataFrame(load_yaml("data/sample/dr_mapping_sample.yaml")["dr_mappings"])

    price_df = pivot_prices(prices)
    volume_df = pivot_volume(prices)
    dr_ohlcv = prices[prices["Ticker"].isin(dr_mapping["DR_Ticker"])]

    outputs = run_topdown_pipeline(
        price_df=price_df,
        volume_df=volume_df,
        metadata_df=metadata,
        asset_mapping_df=asset_map,
        dr_mapping_df=dr_mapping,
        dr_price_df=pivot_prices(dr_ohlcv),
        dr_volume_df=pivot_volume(dr_ohlcv),
    )

    required_tables = [
        "global_flow_summary",
        "country_breadth_summary",
        "thailand_market_health",
        "sector_breadth_summary",
        "cluster_summary",
        "stock_ranking",
        "dr_quality_ranking",
        "redundancy_report",
    ]
    for table_name in required_tables:
        assert table_name in outputs
        assert not outputs[table_name].empty

    excluded = outputs["excluded_securities"]
    assert {"DEMO_DR_ALPHA", "DEMO_ETF_BOND", "DEMO_DW_ALPHA"}.issubset(set(excluded["Ticker"]))
    assert "data_quality_warning" in outputs["dr_quality_ranking"].columns

    report = build_daily_report(outputs)
    assert all("Research signal" in section or "skipped" in section for section in report.values())
    csv_paths = export_report_to_csv(outputs, tmp_path)
    html_path = export_report_to_html(report, tmp_path / "daily_report.html")
    assert csv_paths
    assert html_path.exists()


def test_sample_missing_optional_dr_data_warns_not_crashes():
    prices = pd.read_csv("data/sample/prices_sample.csv", parse_dates=["Date"])
    metadata = pd.read_csv("data/sample/metadata_sample.csv")

    outputs = run_topdown_pipeline(
        price_df=pivot_prices(prices),
        volume_df=pivot_volume(prices),
        metadata_df=metadata,
    )

    warning = outputs["dr_quality_ranking"]["data_quality_warning"].iloc[0]
    assert "DR quality skipped" in warning
    assert not outputs["stock_ranking"].empty
