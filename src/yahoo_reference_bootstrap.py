from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.config_loader import load_yaml


METADATA_COLUMNS = [
    "YahooTicker",
    "Ticker",
    "Name",
    "SecurityType",
    "Sector",
    "Industry",
    "Country",
    "Exchange",
    "Currency",
    "MarketCap",
    "HistoricalStart",
    "HistoricalEnd",
    "RecentAverageVolume20D",
    "Source",
    "VerificationStatus",
    "IsYahooDerived",
    "MissingFields",
    "Notes",
]
SECTOR_MAP_COLUMNS = ["Ticker", "Sector", "Industry", "Source", "VerificationStatus", "IsYahooDerived", "Notes"]
COUNTRY_MAP_COLUMNS = ["Ticker", "Country", "Source", "VerificationStatus", "IsYahooDerived", "Notes"]
ASSET_MAP_COLUMNS = ["Ticker", "asset_class", "group", "subgroup", "Source", "VerificationStatus", "IsYahooDerived", "Notes"]
REPORT_COLUMNS = ["Ticker", "Status", "MissingFields", "HistoryRows", "Notes", "Error"]
REQUIRED_REVIEW_FIELDS = ["Name", "SecurityType", "Sector", "Industry", "Country", "Exchange", "Currency"]


@dataclass(frozen=True)
class YahooBootstrapResult:
    """Candidate reference outputs derived from Yahoo/yfinance metadata."""

    metadata: pd.DataFrame
    sector_map: pd.DataFrame
    country_map: pd.DataFrame
    asset_map: pd.DataFrame
    download_report: pd.DataFrame


def configured_yahoo_tickers(config_path: str | Path = "config/data_sources.yaml") -> list[str]:
    """Return configured Yahoo tickers from data_sources.yaml without network calls."""
    config = load_yaml(config_path)
    yahoo_settings = config.get("source_settings", {}).get("yahoo", {})
    return normalize_tickers(yahoo_settings.get("tickers") or [])


def normalize_tickers(tickers: Iterable[object]) -> list[str]:
    """Return unique non-empty ticker strings while preserving input order."""
    seen: set[str] = set()
    result: list[str] = []
    for ticker in tickers:
        text = str(ticker).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def bootstrap_yahoo_reference_candidates(
    tickers: Iterable[object],
    yfinance_module: Any,
    asset_hint_map: dict[str, dict[str, str]] | None = None,
    history_period: str = "max",
) -> YahooBootstrapResult:
    """Fetch Yahoo-derived reference candidates.

    These candidates are intentionally marked as NeedsReview and must not be
    treated as verified production reference data.
    """
    rows: list[dict[str, object]] = []
    report_rows: list[dict[str, object]] = []
    hints = asset_hint_map or {}
    for ticker in normalize_tickers(tickers):
        try:
            candidate, history_rows = _candidate_for_ticker(ticker, yfinance_module, hints, history_period)
            missing_fields = missing_review_fields(candidate)
            candidate["MissingFields"] = ", ".join(missing_fields)
            candidate["Notes"] = _candidate_notes(ticker, candidate, hints)
            rows.append(candidate)
            report_rows.append(
                {
                    "Ticker": ticker,
                    "Status": "Fetched",
                    "MissingFields": ", ".join(missing_fields),
                    "HistoryRows": history_rows,
                    "Notes": candidate["Notes"],
                    "Error": "",
                }
            )
        except Exception as exc:
            rows.append(_empty_candidate(ticker, notes="Yahoo metadata fetch failed; manual review required."))
            report_rows.append(
                {
                    "Ticker": ticker,
                    "Status": "Error",
                    "MissingFields": ", ".join(REQUIRED_REVIEW_FIELDS),
                    "HistoryRows": 0,
                    "Notes": "No candidate row should be promoted until reviewed.",
                    "Error": str(exc),
                }
            )

    metadata = pd.DataFrame(rows, columns=METADATA_COLUMNS)
    return YahooBootstrapResult(
        metadata=metadata,
        sector_map=build_sector_map_candidates(metadata),
        country_map=build_country_map_candidates(metadata),
        asset_map=build_asset_map_candidates(metadata, hints),
        download_report=pd.DataFrame(report_rows, columns=REPORT_COLUMNS),
    )


def load_asset_hint_map(path: str | Path | None = "data/reference/asset_map_sample.csv") -> dict[str, dict[str, str]]:
    """Load existing/sample asset-class hints for configured proxy tickers only."""
    if path is None or not Path(path).exists():
        return {}
    table = pd.read_csv(path)
    required = {"Ticker", "asset_class", "group", "subgroup"}
    if not required.issubset(table.columns):
        return {}
    hints: dict[str, dict[str, str]] = {}
    for _, row in table.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        if not ticker:
            continue
        hints[ticker] = {
            "asset_class": _clean_value(row.get("asset_class")),
            "group": _clean_value(row.get("group")),
            "subgroup": _clean_value(row.get("subgroup")),
        }
    return hints


def build_sector_map_candidates(metadata: pd.DataFrame) -> pd.DataFrame:
    """Build sector-map candidates from reviewed Yahoo metadata candidates."""
    if metadata.empty:
        return pd.DataFrame(columns=SECTOR_MAP_COLUMNS)
    rows = []
    for _, row in metadata.iterrows():
        sector = _clean_value(row.get("Sector"))
        industry = _clean_value(row.get("Industry"))
        if sector or industry:
            rows.append(
                {
                    "Ticker": row["Ticker"],
                    "Sector": sector,
                    "Industry": industry,
                    "Source": "Yahoo",
                    "VerificationStatus": "NeedsReview",
                    "IsYahooDerived": True,
                    "Notes": "Candidate sector/industry from Yahoo; verify before promotion.",
                }
            )
    return pd.DataFrame(rows, columns=SECTOR_MAP_COLUMNS)


def build_country_map_candidates(metadata: pd.DataFrame) -> pd.DataFrame:
    """Build country-map candidates from reviewed Yahoo metadata candidates."""
    if metadata.empty:
        return pd.DataFrame(columns=COUNTRY_MAP_COLUMNS)
    rows = []
    for _, row in metadata.iterrows():
        country = _clean_value(row.get("Country"))
        if country:
            rows.append(
                {
                    "Ticker": row["Ticker"],
                    "Country": country,
                    "Source": "Yahoo",
                    "VerificationStatus": "NeedsReview",
                    "IsYahooDerived": True,
                    "Notes": "Candidate country from Yahoo; verify before promotion.",
                }
            )
    return pd.DataFrame(rows, columns=COUNTRY_MAP_COLUMNS)


def build_asset_map_candidates(metadata: pd.DataFrame, asset_hint_map: dict[str, dict[str, str]] | None = None) -> pd.DataFrame:
    """Build conservative asset-map candidates from crypto fallback or existing hints."""
    if metadata.empty:
        return pd.DataFrame(columns=ASSET_MAP_COLUMNS)
    hints = asset_hint_map or {}
    rows = []
    for _, row in metadata.iterrows():
        ticker = str(row["Ticker"])
        hint = hints.get(ticker)
        if _is_crypto_usd_pair(ticker):
            values = {"asset_class": "Crypto", "group": "Alternative Assets", "subgroup": "Crypto"}
            note = "Crypto fallback from ticker suffix -USD; verify before promotion."
        elif hint:
            values = hint
            note = "Candidate asset class copied from existing configured/sample mapping; verify before promotion."
        else:
            continue
        rows.append(
            {
                "Ticker": ticker,
                "asset_class": values.get("asset_class", ""),
                "group": values.get("group", ""),
                "subgroup": values.get("subgroup", ""),
                "Source": "Yahoo",
                "VerificationStatus": "NeedsReview",
                "IsYahooDerived": True,
                "Notes": note,
            }
        )
    return pd.DataFrame(rows, columns=ASSET_MAP_COLUMNS)


def build_promotion_review_report(result: YahooBootstrapResult) -> pd.DataFrame:
    """Summarize which generated candidates are reviewable for manual promotion."""
    rows = [
        _review_row("metadata", result.metadata, "Review every row before copying into data/reference/metadata.csv."),
        _review_row("sector_map", result.sector_map, "Review sector and industry before copying into data/reference/sector_map.csv."),
        _review_row("country_map", result.country_map, "Review country before copying into data/reference/country_map.csv."),
        _review_row("asset_map", result.asset_map, "Review asset class/group/subgroup before copying into production asset map."),
    ]
    return pd.DataFrame(rows)


def write_candidate_outputs(result: YahooBootstrapResult, output_dir: str | Path) -> dict[str, Path]:
    """Write generated candidate CSV files under a local generated output directory."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    outputs = {
        "metadata": root / "yahoo_metadata_candidates.csv",
        "sector_map": root / "yahoo_sector_map_candidates.csv",
        "country_map": root / "yahoo_country_map_candidates.csv",
        "asset_map": root / "yahoo_asset_map_candidates.csv",
        "download_report": root / "yahoo_download_report.csv",
        "promotion_report": root / "yahoo_promotion_review_report.csv",
    }
    result.metadata.to_csv(outputs["metadata"], index=False)
    result.sector_map.to_csv(outputs["sector_map"], index=False)
    result.country_map.to_csv(outputs["country_map"], index=False)
    result.asset_map.to_csv(outputs["asset_map"], index=False)
    result.download_report.to_csv(outputs["download_report"], index=False)
    build_promotion_review_report(result).to_csv(outputs["promotion_report"], index=False)
    return outputs


def read_candidate_outputs(output_dir: str | Path) -> YahooBootstrapResult:
    """Read generated candidate outputs for validation/report-only workflows."""
    root = Path(output_dir)
    return YahooBootstrapResult(
        metadata=_read_csv_or_empty(root / "yahoo_metadata_candidates.csv", METADATA_COLUMNS),
        sector_map=_read_csv_or_empty(root / "yahoo_sector_map_candidates.csv", SECTOR_MAP_COLUMNS),
        country_map=_read_csv_or_empty(root / "yahoo_country_map_candidates.csv", COUNTRY_MAP_COLUMNS),
        asset_map=_read_csv_or_empty(root / "yahoo_asset_map_candidates.csv", ASSET_MAP_COLUMNS),
        download_report=_read_csv_or_empty(root / "yahoo_download_report.csv", REPORT_COLUMNS),
    )


def _candidate_for_ticker(
    ticker: str,
    yfinance_module: Any,
    asset_hint_map: dict[str, dict[str, str]],
    history_period: str,
) -> tuple[dict[str, object], int]:
    ticker_obj = yfinance_module.Ticker(ticker)
    info = _ticker_info(ticker_obj)
    history = _ticker_history(ticker_obj, history_period)
    candidate = _empty_candidate(ticker)
    candidate.update(
        {
            "Name": _first_clean(info, ["longName", "shortName", "displayName"]),
            "SecurityType": _clean_value(info.get("quoteType")),
            "Sector": _clean_value(info.get("sector")),
            "Industry": _clean_value(info.get("industry")),
            "Country": _clean_value(info.get("country")),
            "Exchange": _clean_value(info.get("exchange")),
            "Currency": _clean_value(info.get("currency")),
            "MarketCap": _clean_value(info.get("marketCap")),
        }
    )
    _apply_conservative_fallbacks(candidate, ticker, asset_hint_map)
    if not history.empty:
        dates = pd.to_datetime(history.index if history.index.name is not None else history.reset_index().iloc[:, 0], errors="coerce")
        dates = pd.Series(dates).dropna()
        if not dates.empty:
            candidate["HistoricalStart"] = str(dates.min().date())
            candidate["HistoricalEnd"] = str(dates.max().date())
        if "Volume" in history.columns:
            volumes = pd.to_numeric(history["Volume"], errors="coerce").dropna().tail(20)
            if not volumes.empty:
                candidate["RecentAverageVolume20D"] = f"{float(volumes.mean()):.2f}"
    return candidate, len(history)


def _empty_candidate(ticker: str, notes: str = "") -> dict[str, object]:
    return {
        "YahooTicker": ticker,
        "Ticker": ticker,
        "Name": "",
        "SecurityType": "",
        "Sector": "",
        "Industry": "",
        "Country": "",
        "Exchange": "",
        "Currency": "",
        "MarketCap": "",
        "HistoricalStart": "",
        "HistoricalEnd": "",
        "RecentAverageVolume20D": "",
        "Source": "Yahoo",
        "VerificationStatus": "NeedsReview",
        "IsYahooDerived": True,
        "MissingFields": "",
        "Notes": notes,
    }


def _apply_conservative_fallbacks(candidate: dict[str, object], ticker: str, asset_hint_map: dict[str, dict[str, str]]) -> None:
    if _is_crypto_usd_pair(ticker):
        candidate["Country"] = candidate["Country"] or "Global"
        candidate["Sector"] = candidate["Sector"] or "Crypto"
        candidate["Industry"] = candidate["Industry"] or "Crypto"
        candidate["SecurityType"] = candidate["SecurityType"] or "Crypto"
    elif ticker in asset_hint_map and not candidate["Sector"]:
        candidate["Sector"] = asset_hint_map[ticker].get("asset_class", "")


def _candidate_notes(ticker: str, candidate: dict[str, object], asset_hint_map: dict[str, dict[str, str]]) -> str:
    notes = ["Yahoo-derived candidate; requires manual verification before production use."]
    if _is_crypto_usd_pair(ticker):
        notes.append("Applied conservative crypto fallback from -USD ticker suffix.")
    if ticker in asset_hint_map:
        notes.append("Existing asset-map hint is available for review.")
    if candidate.get("MissingFields"):
        notes.append("Missing fields must be filled or accepted manually.")
    return " ".join(notes)


def missing_review_fields(candidate: dict[str, object]) -> list[str]:
    """Return candidate fields still missing after Yahoo fetch and conservative fallbacks."""
    return [field for field in REQUIRED_REVIEW_FIELDS if not _clean_value(candidate.get(field))]


def _ticker_info(ticker_obj: Any) -> dict[str, object]:
    getter = getattr(ticker_obj, "get_info", None)
    if callable(getter):
        info = getter()
    else:
        info = getattr(ticker_obj, "info", {})
    return info if isinstance(info, dict) else {}


def _ticker_history(ticker_obj: Any, history_period: str) -> pd.DataFrame:
    history = getattr(ticker_obj, "history", None)
    if not callable(history):
        return pd.DataFrame()
    result = history(period=history_period, auto_adjust=False)
    return result if isinstance(result, pd.DataFrame) else pd.DataFrame()


def _first_clean(values: dict[str, object], keys: list[str]) -> str:
    for key in keys:
        value = _clean_value(values.get(key))
        if value:
            return value
    return ""


def _clean_value(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _is_crypto_usd_pair(ticker: str) -> bool:
    return ticker.upper().endswith("-USD")


def _review_row(name: str, table: pd.DataFrame, note: str) -> dict[str, object]:
    needs_review = int(table["VerificationStatus"].eq("NeedsReview").sum()) if "VerificationStatus" in table.columns else 0
    return {
        "candidate_file": name,
        "rows": len(table),
        "needs_review_rows": needs_review,
        "can_promote_manually": needs_review > 0,
        "notes": note,
    }


def _read_csv_or_empty(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    return pd.read_csv(path)
