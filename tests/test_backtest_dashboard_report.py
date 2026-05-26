import pandas as pd

from src.dashboard import build_backtest_dashboard_tables
from src.report_generator import build_backtest_report_tables, build_daily_report, export_report_to_csv


def _backtest_outputs():
    return {
        "backtest_summary": pd.DataFrame(
            {
                "total_return": [0.12],
                "annualized_volatility": [0.18],
                "max_drawdown": [-0.05],
                "hit_rate": [0.55],
                "average_gross_exposure": [0.8],
                "observations": [20],
                "signal_type": ["research signal only"],
            }
        ),
        "backtest_portfolio": pd.DataFrame(
            {
                "portfolio_return": [0.01, -0.02],
                "equity": [1.01, 0.9898],
                "drawdown": [0.0, -0.02],
                "gross_exposure": [0.8, 0.7],
                "turnover": [0.2, 0.1],
                "signal_type": ["research signal only", "research signal only"],
            }
        ),
        "backtest_positions": pd.DataFrame({"AAA": [0.5, 0.4], "BBB": [0.3, 0.3]}),
        "backtest_instrument_metrics": pd.DataFrame({"Ticker": ["AAA"], "total_return": [0.1]}),
        "backtest_warnings": pd.DataFrame({"warning": ["demo warning"]}),
    }


def test_backtest_dashboard_tables_only_include_non_empty_outputs():
    outputs = _backtest_outputs()
    outputs["backtest_warnings"] = pd.DataFrame()

    tables = build_backtest_dashboard_tables(outputs)

    assert "Backtest Assumption Summary" in tables
    assert "Backtest Portfolio Path" in tables
    assert "Backtest Warnings" not in tables


def test_daily_report_includes_backtest_research_assumption_label():
    report = build_daily_report(_backtest_outputs())

    assert "backtest" in report
    assert "Research signal - backtest assumptions" in report["backtest"]
    assert "not financial advice" in report["backtest"]
    assert "total_return=0.1200" in report["backtest"]


def test_backtest_report_tables_export_to_csv(tmp_path):
    outputs = _backtest_outputs()

    tables = build_backtest_report_tables(outputs)
    paths = export_report_to_csv(tables, tmp_path)

    assert set(tables) == {
        "backtest_summary",
        "backtest_portfolio",
        "backtest_positions",
        "backtest_instrument_metrics",
        "backtest_warnings",
    }
    assert {path.name for path in paths} == {f"{name}.csv" for name in tables}
