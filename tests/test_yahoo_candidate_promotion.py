from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.yahoo_candidate_promotion import (
    backup_existing_outputs,
    build_ticker_coverage_report,
    promote_reviewed_yahoo_candidates,
    validate_candidate_table,
)


def _write_config(path: Path, tickers: list[str]) -> None:
    body = "\n".join(f"      - {ticker}" for ticker in tickers)
    path.write_text(
        "active_source: yahoo\n"
        "source_settings:\n"
        "  yahoo:\n"
        "    tickers:\n"
        f"{body}\n",
        encoding="utf-8",
    )


def _reviewed_candidates(candidate_dir: Path, status: str = "Reviewed") -> None:
    candidate_dir.mkdir(parents=True, exist_ok=True)
    audit = {"Source": "Yahoo", "VerificationStatus": status, "IsYahooDerived": True, "Notes": "manual review complete"}
    pd.DataFrame(
        [
            {
                "YahooTicker": "AAA",
                "Ticker": "AAA",
                "Name": "AAA Corp",
                "SecurityType": "ETF",
                "Sector": "Technology",
                "Industry": "Software",
                "Country": "United States",
                "Exchange": "NMS",
                "Currency": "USD",
                "MarketCap": "1000",
                "HistoricalStart": "2024-01-01",
                "HistoricalEnd": "2024-01-31",
                "RecentAverageVolume20D": "123.00",
                "MissingFields": "",
                "Universe": "Global",
                "Suspended": False,
                **audit,
            }
        ]
    ).to_csv(candidate_dir / "yahoo_metadata_candidates.csv", index=False)
    pd.DataFrame([{"Ticker": "AAA", "Sector": "Technology", "Industry": "Software", **audit}]).to_csv(
        candidate_dir / "yahoo_sector_map_candidates.csv", index=False
    )
    pd.DataFrame([{"Ticker": "AAA", "Country": "United States", **audit}]).to_csv(
        candidate_dir / "yahoo_country_map_candidates.csv", index=False
    )
    pd.DataFrame([{"Ticker": "AAA", "asset_class": "Equity", "group": "Risk Assets", "subgroup": "Software", **audit}]).to_csv(
        candidate_dir / "yahoo_asset_map_candidates.csv", index=False
    )


def test_dry_run_filters_only_reviewed_rows_and_writes_nothing(tmp_path):
    candidate_dir = tmp_path / "generated"
    output_dir = tmp_path / "reference"
    config_path = tmp_path / "data_sources.yaml"
    _write_config(config_path, ["AAA", "BBB"])
    _reviewed_candidates(candidate_dir)

    plan = promote_reviewed_yahoo_candidates(candidate_dir, output_dir, config_path=config_path)

    assert plan.apply is False
    assert plan.has_errors is False
    assert plan.outputs["metadata"]["Ticker"].tolist() == ["AAA"]
    assert not (output_dir / "metadata.csv").exists()
    metadata_coverage = plan.coverage_report[plan.coverage_report["file"].eq("metadata")].iloc[0]
    assert metadata_coverage["status"] == "gap"
    assert metadata_coverage["missing_configured_tickers"] == "BBB"


def test_needs_review_rows_block_promotion(tmp_path):
    candidate_dir = tmp_path / "generated"
    output_dir = tmp_path / "reference"
    config_path = tmp_path / "data_sources.yaml"
    _write_config(config_path, ["AAA"])
    _reviewed_candidates(candidate_dir, status="NeedsReview")

    plan = promote_reviewed_yahoo_candidates(candidate_dir, output_dir, config_path=config_path)

    assert plan.has_errors is True
    assert any(plan.validation_report["check"].eq("review_status"))
    assert plan.outputs["metadata"].empty
    with pytest.raises(ValueError, match="Promotion blocked"):
        promote_reviewed_yahoo_candidates(candidate_dir, output_dir, config_path=config_path, apply=True)


def test_blank_important_fields_are_errors_unless_allowed(tmp_path):
    candidate_dir = tmp_path / "generated"
    _reviewed_candidates(candidate_dir)
    table = pd.read_csv(candidate_dir / "yahoo_metadata_candidates.csv")
    table.loc[0, "Universe"] = ""

    errors = validate_candidate_table("metadata", table, {"Reviewed", "Approved"})
    allowed = validate_candidate_table("metadata", table, {"Reviewed", "Approved"}, {"Universe"})

    assert any("Universe is blank" in row["detail"] for row in errors)
    assert not any("Universe is blank" in row["detail"] for row in allowed)


def test_apply_writes_outputs_and_backs_up_existing_files(tmp_path):
    candidate_dir = tmp_path / "generated"
    output_dir = tmp_path / "reference"
    config_path = tmp_path / "data_sources.yaml"
    _write_config(config_path, ["AAA"])
    _reviewed_candidates(candidate_dir, status="Approved")
    output_dir.mkdir()
    (output_dir / "metadata.csv").write_text("old,data\n", encoding="utf-8")

    plan = promote_reviewed_yahoo_candidates(candidate_dir, output_dir, config_path=config_path, apply=True)

    assert (output_dir / "metadata.csv").exists()
    assert pd.read_csv(output_dir / "metadata.csv").loc[0, "VerificationStatus"] == "Approved"
    assert "metadata" in plan.backups
    assert plan.backups["metadata"].exists()
    assert plan.written_paths["asset_map"] == output_dir / "asset_map.csv"


def test_backup_existing_outputs_only_copies_present_files(tmp_path):
    output_dir = tmp_path / "reference"
    output_dir.mkdir()
    (output_dir / "country_map.csv").write_text("Ticker,Country\nAAA,United States\n", encoding="utf-8")

    backups = backup_existing_outputs(output_dir, timestamp="20260102030405")

    assert set(backups) == {"country_map"}
    assert backups["country_map"].name == "country_map.20260102030405.csv"


def test_coverage_report_tracks_extra_promoted_tickers():
    report = build_ticker_coverage_report({"metadata": pd.DataFrame({"Ticker": ["AAA", "EXTRA"]})}, ["AAA", "BBB"])

    row = report.iloc[0]
    assert row["missing_configured_tickers"] == "BBB"
    assert row["extra_promoted_tickers"] == "EXTRA"
