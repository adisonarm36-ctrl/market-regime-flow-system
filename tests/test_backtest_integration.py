import pandas as pd

from src.backtest import BacktestConfig
from src.backtest_integration import build_backtest_data_coverage_warnings, build_pipeline_backtest_signals
from src.data_adapters.base import DataAdapter
from src.topdown_pipeline import run_pipeline_from_config, run_topdown_pipeline


class MockYahooBacktestAdapter(DataAdapter):
    def __init__(self, prices: pd.DataFrame, metadata: pd.DataFrame) -> None:
        self.prices = prices
        self.metadata = metadata
        self.warnings = ["mock Yahoo historical prices loaded"]

    def load_prices(self) -> pd.DataFrame:
        return self.prices

    def load_metadata(self) -> pd.DataFrame:
        return self.metadata

    def load_sector_map(self) -> pd.DataFrame:
        return pd.DataFrame()

    def load_dr_mapping(self) -> pd.DataFrame:
        return pd.DataFrame()

    def validate_schema(self) -> list[str]:
        return []


def _yahoo_like_prices(tickers: list[str], periods: int = 260) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=periods, freq="B")
    rows = []
    for ticker_index, ticker in enumerate(tickers):
        for i, day in enumerate(dates):
            close = 100 + ticker_index * 20 + i * (0.5 + ticker_index * 0.1)
            rows.append(
                {
                    "Date": day,
                    "Ticker": ticker,
                    "Open": close - 0.1,
                    "High": close + 0.3,
                    "Low": close - 0.3,
                    "Close": close * 0.95,
                    "Volume": 1000 + i,
                    "Adjusted Close": close,
                }
            )
    return pd.DataFrame(rows)


def test_pipeline_backtest_outputs_when_enabled():
    dates = pd.date_range("2026-01-01", periods=260)
    price = pd.DataFrame({"AAA": range(100, 360), "BBB": range(360, 100, -1)}, index=dates, dtype=float)
    volume = pd.DataFrame({"AAA": [100] * 260, "BBB": [200] * 260}, index=dates, dtype=float)
    metadata = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB"],
            "Country": ["United States", "United States"],
            "Sector": ["Tech", "Energy"],
            "SecurityType": ["Stock", "Stock"],
        }
    )

    outputs = run_topdown_pipeline(
        price_df=price,
        volume_df=volume,
        metadata_df=metadata,
        country_map_df=metadata[["Ticker", "Country"]],
        backtest_enabled=True,
        backtest_config=BacktestConfig(max_position_weight=1.0),
    )

    assert not outputs["backtest_summary"].empty
    assert not outputs["backtest_portfolio"].empty
    assert not outputs["backtest_positions"].empty
    assert outputs["backtest_summary"].iloc[0]["signal_type"] == "research signal only"


def test_pipeline_backtest_uses_supplied_signal_table():
    dates = pd.date_range("2026-01-01", periods=4)
    price = pd.DataFrame({"AAA": [100.0, 101.0, 102.0, 103.0]}, index=dates)
    signals = pd.DataFrame({"AAA": [1.0, 1.0, 1.0, 1.0]}, index=dates)

    outputs = run_topdown_pipeline(
        price_df=price,
        metadata_df=pd.DataFrame({"Ticker": ["AAA"], "Country": ["US"], "Sector": ["Tech"], "SecurityType": ["Stock"]}),
        backtest_enabled=True,
        backtest_signal_df=signals,
        backtest_config=BacktestConfig(max_position_weight=1.0),
    )

    assert "AAA" in outputs["backtest_positions"].columns
    assert outputs["backtest_summary"].iloc[0]["observations"] == 4


def test_pipeline_backtest_maps_dr_signal_to_underlying_and_not_dr_price():
    dates = pd.date_range("2026-01-01", periods=4)
    price = pd.DataFrame(
        {
            "UNDER_A": [100.0, 101.0, 102.0, 103.0],
            "DEMO_DR": [10.0, 9.0, 8.0, 7.0],
        },
        index=dates,
    )
    stock_ranking = pd.DataFrame(
        {
            "Ticker": ["DEMO_DR"],
            "UnderlyingTicker": ["UNDER_A"],
            "SecurityType": ["DR"],
            "research_score": [90.0],
            "failed_filters": [""],
        }
    )
    mapping = pd.DataFrame({"DR_Ticker": ["DEMO_DR"], "UnderlyingTicker": ["UNDER_A"]})

    signals, warnings = build_pipeline_backtest_signals(price, stock_ranking, mapping)

    assert "UNDER_A" in signals.columns
    assert "DEMO_DR" not in signals.columns
    assert warnings == []


def test_pipeline_backtest_reports_missing_dr_underlying_price():
    dates = pd.date_range("2026-01-01", periods=4)
    price = pd.DataFrame({"DEMO_DR": [10.0, 11.0, 12.0, 13.0]}, index=dates)
    stock_ranking = pd.DataFrame(
        {
            "Ticker": ["DEMO_DR"],
            "UnderlyingTicker": ["UNDER_A"],
            "SecurityType": ["DR"],
            "research_score": [90.0],
            "failed_filters": [""],
        }
    )

    signals, warnings = build_pipeline_backtest_signals(price, stock_ranking)

    assert signals.empty
    assert "backtest DR signal skipped: DEMO_DR underlying UNDER_A missing price data" in warnings


def test_pipeline_backtest_skips_failed_filters():
    dates = pd.date_range("2026-01-01", periods=4)
    price = pd.DataFrame({"AAA": [100.0, 101.0, 102.0, 103.0]}, index=dates)
    stock_ranking = pd.DataFrame(
        {
            "Ticker": ["AAA"],
            "SecurityType": ["Stock"],
            "research_score": [75.0],
            "failed_filters": ["redundancy"],
        }
    )

    signals, warnings = build_pipeline_backtest_signals(price, stock_ranking)

    assert signals.empty
    assert "backtest signal skipped: AAA failed filters" in warnings


def test_config_yahoo_backtest_uses_loaded_historical_prices_with_coverage_warnings(tmp_path):
    prices = _yahoo_like_prices(["AAA", "BBB"])
    metadata = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB"],
            "Country": ["United States", "United States"],
            "Sector": ["Tech", "Energy"],
            "Industry": ["Software", "Oil"],
            "Universe": ["Demo", "Demo"],
            "SecurityType": ["Stock", "Stock"],
            "Suspended": [False, False],
        }
    )
    config_path = tmp_path / "data_sources.yaml"
    config_path.write_text(
        "active_source: yahoo\n"
        "source_settings:\n"
        "  yahoo:\n"
        "    tickers:\n"
        "      - AAA\n"
        "      - BBB\n",
        encoding="utf-8",
    )
    adapter = MockYahooBacktestAdapter(prices, metadata)

    outputs = run_pipeline_from_config(
        config_path=str(config_path),
        adapter=adapter,
        backtest_enabled=True,
        backtest_config=BacktestConfig(max_position_weight=1.0),
    )

    assert not outputs["backtest_summary"].empty
    assert "AAA" in outputs["backtest_positions"].columns
    warnings = outputs["backtest_warnings"]["warning"].tolist()
    assert any("backtest source: Yahoo historical prices" in warning for warning in warnings)
    assert any("historical research assumptions only" in warning for warning in warnings)
    assert any("backtest coverage:" in warning for warning in warnings)


def test_backtest_coverage_warnings_report_missing_yahoo_price_tickers():
    dates = pd.date_range("2026-01-01", periods=4)
    price = pd.DataFrame({"AAA": [100.0, 101.0, 102.0, 103.0]}, index=dates)
    signals = pd.DataFrame({"AAA": [1.0, 1.0, 1.0, 1.0], "BBB": [1.0, 1.0, 1.0, 1.0]}, index=dates)

    warnings = build_backtest_data_coverage_warnings(price, signals, "Yahoo historical prices")

    assert "backtest source: Yahoo historical prices; historical research assumptions only, not financial advice" in warnings
    assert "backtest coverage warning: signal tickers missing price data: BBB" in warnings
