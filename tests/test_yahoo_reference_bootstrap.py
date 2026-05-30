from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.yahoo_reference_bootstrap import (
    bootstrap_yahoo_reference_candidates,
    build_promotion_review_report,
    configured_yahoo_tickers,
    load_asset_hint_map,
    normalize_tickers,
    read_candidate_outputs,
    write_candidate_outputs,
)


class FakeTicker:
    def __init__(self, info: dict[str, object], history: pd.DataFrame | None = None, error: Exception | None = None) -> None:
        self._info = info
        self._history = history if history is not None else pd.DataFrame()
        self._error = error

    def get_info(self) -> dict[str, object]:
        if self._error:
            raise self._error
        return self._info

    def history(self, period: str = "max", auto_adjust: bool = False) -> pd.DataFrame:
        return self._history


class FakeYFinance:
    def __init__(self, tickers: dict[str, FakeTicker]) -> None:
        self.tickers = tickers

    def Ticker(self, ticker: str) -> FakeTicker:
        return self.tickers[ticker]


def test_configured_yahoo_tickers_reads_data_sources_without_network(tmp_path):
    config_path = tmp_path / "data_sources.yaml"
    config_path.write_text(
        "active_source: yahoo\n"
        "source_settings:\n"
        "  yahoo:\n"
        "    tickers:\n"
        "      - SPY\n"
        "      - ''\n"
        "      - SPY\n"
        "      - BTC-USD\n",
        encoding="utf-8",
    )

    assert configured_yahoo_tickers(config_path) == ["SPY", "BTC-USD"]
    assert normalize_tickers([" AAA ", "", "AAA", "BBB"]) == ["AAA", "BBB"]


def test_bootstrap_yahoo_reference_candidates_marks_all_rows_needs_review():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    history = pd.DataFrame({"Volume": [100, 200, 300]}, index=dates)
    yf = FakeYFinance(
        {
            "AAA": FakeTicker(
                {
                    "longName": "AAA Corp",
                    "quoteType": "EQUITY",
                    "sector": "Technology",
                    "industry": "Software",
                    "country": "United States",
                    "exchange": "NMS",
                    "currency": "USD",
                    "marketCap": 123456,
                },
                history,
            ),
            "BTC-USD": FakeTicker({"shortName": "Bitcoin USD", "currency": "USD"}, history),
        }
    )

    result = bootstrap_yahoo_reference_candidates(
        ["AAA", "BTC-USD"],
        yfinance_module=yf,
        asset_hint_map={"AAA": {"asset_class": "Equity", "group": "Risk Assets", "subgroup": "Software"}},
    )

    assert result.metadata["Source"].eq("Yahoo").all()
    assert result.metadata["VerificationStatus"].eq("NeedsReview").all()
    assert result.metadata["IsYahooDerived"].eq(True).all()
    aaa = result.metadata[result.metadata["Ticker"].eq("AAA")].iloc[0]
    assert aaa["Name"] == "AAA Corp"
    assert aaa["RecentAverageVolume20D"] == "200.00"
    assert aaa["HistoricalStart"] == "2024-01-02"
    assert aaa["MissingFields"] == ""
    assert bool(aaa["IsFallbackDerived"]) is False
    crypto = result.metadata[result.metadata["Ticker"].eq("BTC-USD")].iloc[0]
    assert crypto["Country"] == "Global"
    assert crypto["Sector"] == "Crypto"
    assert crypto["SecurityType"] == "Crypto"
    assert bool(crypto["IsFallbackDerived"]) is True
    assert "Country" in crypto["FallbackFields"]
    assert "Exchange" in crypto["MissingFields"]
    assert result.sector_map["Ticker"].tolist() == ["AAA", "BTC-USD"]
    assert result.sector_map["YahooTicker"].tolist() == ["AAA", "BTC-USD"]
    assert result.sector_map["VerificationStatus"].eq("NeedsReview").all()
    assert result.sector_map.loc[result.sector_map["Ticker"].eq("BTC-USD"), "IsFallbackDerived"].iloc[0] == True
    assert result.country_map["Ticker"].tolist() == ["AAA", "BTC-USD"]
    assert result.country_map["YahooTicker"].tolist() == ["AAA", "BTC-USD"]
    assert result.country_map["VerificationStatus"].eq("NeedsReview").all()
    assert set(result.asset_map["Ticker"]) == {"AAA", "BTC-USD"}
    assert result.download_report["Status"].tolist() == ["Fetched", "Fetched"]
    assert "Yahoo metadata" in result.download_report.loc[0, "SectorMapStatus"]
    assert "conservative fallback" in result.download_report.loc[1, "CountryMapStatus"]


def test_sector_candidates_use_asset_hint_fallback_without_country_inference():
    yf = FakeYFinance(
        {
            "SPY": FakeTicker({"shortName": "SPY", "quoteType": "ETF", "currency": "USD"}),
        }
    )

    result = bootstrap_yahoo_reference_candidates(
        ["SPY"],
        yfinance_module=yf,
        asset_hint_map={"SPY": {"asset_class": "Equity", "group": "Risk Assets", "subgroup": "Broad Market"}},
    )

    assert result.metadata.loc[0, "Sector"] == "Equity"
    assert result.metadata.loc[0, "IsFallbackDerived"] == True
    assert result.metadata.loc[0, "FallbackFields"] == "Sector"
    assert result.sector_map.loc[0, "Ticker"] == "SPY"
    assert result.sector_map.loc[0, "YahooTicker"] == "SPY"
    assert result.sector_map.loc[0, "Sector"] == "Equity"
    assert result.sector_map.loc[0, "IsFallbackDerived"] == True
    assert "Industry" in result.sector_map.loc[0, "MissingFields"]
    assert result.country_map.empty
    assert "No country map row generated" in result.download_report.loc[0, "CountryMapStatus"]


def test_bootstrap_records_errors_without_stopping_other_tickers():
    yf = FakeYFinance(
        {
            "BAD": FakeTicker({}, error=RuntimeError("metadata unavailable")),
        }
    )

    result = bootstrap_yahoo_reference_candidates(["BAD"], yfinance_module=yf)

    assert result.metadata.loc[0, "Ticker"] == "BAD"
    assert result.metadata.loc[0, "VerificationStatus"] == "NeedsReview"
    assert result.download_report.loc[0, "Status"] == "Error"
    assert "metadata unavailable" in result.download_report.loc[0, "Error"]


def test_write_and_validate_candidate_outputs_are_local_artifacts(tmp_path):
    yf = FakeYFinance({"AAA": FakeTicker({"shortName": "AAA", "quoteType": "ETF", "country": "United States"})})
    result = bootstrap_yahoo_reference_candidates(["AAA"], yfinance_module=yf)

    paths = write_candidate_outputs(result, tmp_path)
    loaded = read_candidate_outputs(tmp_path)
    report = build_promotion_review_report(loaded)

    assert paths["metadata"].name == "yahoo_metadata_candidates.csv"
    assert Path(paths["download_report"]).exists()
    assert loaded.metadata.loc[0, "VerificationStatus"] == "NeedsReview"
    assert report["candidate_file"].tolist() == ["metadata", "sector_map", "country_map", "asset_map"]
    assert bool(report.loc[report["candidate_file"].eq("metadata"), "can_promote_manually"].iloc[0]) is True


def test_asset_hint_loader_uses_existing_mapping_without_inventing_unknowns(tmp_path):
    path = tmp_path / "asset_map.csv"
    path.write_text(
        "Ticker,asset_class,group,subgroup\n"
        "SPY,Equity,Risk Assets,Broad Market\n",
        encoding="utf-8",
    )

    assert load_asset_hint_map(path) == {
        "SPY": {"asset_class": "Equity", "group": "Risk Assets", "subgroup": "Broad Market"}
    }
