import pandas as pd

from src.report_generator import build_daily_report, export_report_to_csv, export_report_to_html


def test_report_generator_uses_metric_values_and_exports(tmp_path):
    outputs = {
        "global_flow_summary": pd.DataFrame({"Ticker": ["AAA"], "flow_score": [88.2], "flow_classification": ["Strong Inflow"]}),
        "country_breadth_summary": pd.DataFrame({"country": ["Thailand"], "breadth_score": [66.0], "regime": ["Bull"]}),
        "thailand_market_health": pd.DataFrame({"universe": ["SET ex-DR"], "breadth_score": [64.0], "regime": ["Bull"], "pct_above_50ma": [70], "pct_above_200ma": [60]}),
        "sector_breadth_summary": pd.DataFrame({"Sector": ["Tech"], "breadth_score": [75.0], "regime": ["Strong Bull"]}),
        "cluster_summary": pd.DataFrame({"cluster": [1], "cluster_score": [90.0], "cluster_momentum": [0.12]}),
        "stock_ranking": pd.DataFrame({"Ticker": ["AAA"], "research_score": [82.0], "failed_filters": [""]}),
        "dr_quality_ranking": pd.DataFrame({"DR_Ticker": ["AAA80"], "Underlying_Ticker": ["AAA"], "dr_quality_score": [77.0], "execution_rank": [1]}),
    }

    report = build_daily_report(outputs)
    csv_paths = export_report_to_csv(outputs, tmp_path)
    html_path = export_report_to_html(report, tmp_path / "daily.html")

    assert "flow_score=88.20" in report["global_flow"]
    assert csv_paths
    assert html_path.exists()
