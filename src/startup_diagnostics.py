from __future__ import annotations

from dataclasses import dataclass
from importlib import util
from pathlib import Path
from typing import Any

import pandas as pd


YFINANCE_INSTALL_COMMAND = r".\.venv\Scripts\python.exe -m pip install -r requirements.txt"
STREAMLIT_VENV_RUN_COMMAND = r".\.venv\Scripts\python.exe -m streamlit run app.py"


@dataclass(frozen=True)
class DependencyDiagnostic:
    """Import availability diagnostic for a dashboard runtime dependency."""

    package: str
    importable: bool
    summary: str
    fix_commands: tuple[str, ...] = ()


@dataclass(frozen=True)
class StartupChecklistRow:
    """One dashboard startup checklist row."""

    item: str
    status: str
    detail: str
    next_step: str = ""


@dataclass(frozen=True)
class YahooSmokeTestResult:
    """Summary of one explicit Yahoo historical smoke-test run."""

    attempted_tickers: tuple[str, ...]
    rows_loaded: int
    start_date: str
    end_date: str
    cache_path: str
    cache_exists_before: bool
    cache_exists_after: bool
    cache_status: str
    warnings: tuple[str, ...] = ()
    error: str = ""


def check_yfinance_available(find_spec=util.find_spec) -> DependencyDiagnostic:
    """Check whether yfinance is importable in the active Python environment."""
    importable = find_spec("yfinance") is not None
    if importable:
        return DependencyDiagnostic(
            package="yfinance",
            importable=True,
            summary="yfinance is available in this Python environment.",
        )
    return DependencyDiagnostic(
        package="yfinance",
        importable=False,
        summary="yfinance is not importable in this Python environment. Yahoo historical loading is unavailable until dependencies are installed.",
        fix_commands=(YFINANCE_INSTALL_COMMAND, STREAMLIT_VENV_RUN_COMMAND),
    )


def yfinance_missing_guidance(diagnostic: DependencyDiagnostic) -> str:
    """Return user-facing guidance for missing yfinance dependency."""
    if diagnostic.importable:
        return diagnostic.summary
    commands = "\n".join(diagnostic.fix_commands)
    return (
        f"{diagnostic.summary}\n\n"
        "Run Streamlit with the project virtual environment:\n\n"
        f"{commands}"
    )


def build_yahoo_startup_checklist(
    config: dict | None,
    yfinance_diagnostic: DependencyDiagnostic,
    cache_status: dict[str, Any] | None = None,
    demo_reference_enabled: bool = False,
    manual_upload_available: bool = True,
    adapter_error: str | None = None,
) -> list[StartupChecklistRow]:
    """Build Yahoo-first startup checklist rows without loading data or calling the network."""
    rows: list[StartupChecklistRow] = []
    if not config:
        return [
            StartupChecklistRow(
                item="data_sources.yaml",
                status="blocker",
                detail="Configuration file could not be loaded.",
                next_step="Use manual upload fallback or restore config/data_sources.yaml.",
            )
        ]

    active_source = config.get("active_source", "csv")
    rows.append(
        StartupChecklistRow(
            item="active_source",
            status="ok" if active_source == "yahoo" else "warning",
            detail=f"active_source is {active_source}.",
            next_step="Set active_source to yahoo for Yahoo-first historical loading." if active_source != "yahoo" else "",
        )
    )
    rows.append(
        StartupChecklistRow(
            item="Manual upload fallback",
            status="ok" if manual_upload_available else "warning",
            detail="Advanced / fallback manual upload is available." if manual_upload_available else "Manual upload fallback is unavailable.",
            next_step="" if manual_upload_available else "Restore the manual upload fallback workflow.",
        )
    )

    if active_source != "yahoo":
        return rows

    yahoo_settings = config.get("source_settings", {}).get("yahoo", {})
    tickers = [str(ticker).strip() for ticker in yahoo_settings.get("tickers") or [] if str(ticker).strip()]
    rows.append(
        StartupChecklistRow(
            item="Configured Yahoo tickers",
            status="ok" if tickers else "blocker",
            detail=f"{len(tickers)} configured ticker(s): {', '.join(tickers[:8])}{'...' if len(tickers) > 8 else ''}" if tickers else "No Yahoo tickers are configured.",
            next_step="" if tickers else "Add at least one verified historical Yahoo ticker to config/data_sources.yaml.",
        )
    )
    rows.append(
        StartupChecklistRow(
            item="yfinance availability",
            status="ok" if yfinance_diagnostic.importable else "blocker",
            detail=yfinance_diagnostic.summary,
            next_step="" if yfinance_diagnostic.importable else "Install dependencies and rerun Streamlit with the project virtual environment.",
        )
    )
    if adapter_error:
        rows.append(
            StartupChecklistRow(
                item="Yahoo adapter config",
                status="blocker",
                detail=adapter_error,
                next_step="Fix Yahoo settings in config/data_sources.yaml.",
            )
        )

    cache_dir = yahoo_settings.get("cache_dir") or ""
    rows.append(
        StartupChecklistRow(
            item="Yahoo cache directory",
            status="ok" if str(cache_dir).strip() else "blocker",
            detail=f"Cache directory: {cache_dir}" if str(cache_dir).strip() else "Cache directory is missing.",
            next_step="" if str(cache_dir).strip() else "Set yahoo.cache_dir in config/data_sources.yaml.",
        )
    )
    if cache_status:
        cache_exists = bool(cache_status.get("cache_exists"))
        cache_path = str(cache_status.get("cache_path", ""))
        rows.append(
            StartupChecklistRow(
                item="Yahoo cache file",
                status="ok" if cache_exists else "warning",
                detail=f"Cache file exists: {cache_path}" if cache_exists else f"Cache file not found yet: {cache_path}",
                next_step="" if cache_exists else "Run a historical Yahoo refresh when yfinance is available, or use manual upload fallback.",
            )
        )
        if cache_status.get("cache_is_stale"):
            rows.append(
                StartupChecklistRow(
                    item="Yahoo cache freshness",
                    status="warning",
                    detail="Cache is stale based on configured cache_ttl_hours.",
                    next_step="Refresh historical Yahoo data when network access is appropriate.",
                )
            )
    elif not yfinance_diagnostic.importable:
        rows.append(
            StartupChecklistRow(
                item="Yahoo data loading",
                status="blocker",
                detail="Yahoo historical loading is blocked because yfinance is missing and cache status is unavailable.",
                next_step="Install dependencies, provide a usable cache, or use manual upload fallback.",
            )
        )

    rows.extend(_reference_checklist_rows(yahoo_settings.get("reference_data") or {}, demo_reference_enabled))
    rows.append(
        StartupChecklistRow(
            item="Demo reference mode",
            status="warning" if demo_reference_enabled else "ok",
            detail=(
                "Enabled. Demo reference files are fake/sample data and are not suitable for production research."
                if demo_reference_enabled
                else "Disabled. Production reference paths are used as configured."
            ),
            next_step="Replace demo files with verified local reference files before research use." if demo_reference_enabled else "",
        )
    )
    rows.append(
        StartupChecklistRow(
            item="Yahoo data boundary",
            status="ok",
            detail="Yahoo is historical OHLCV only. Local reference files are required for metadata, mappings, and research layers.",
        )
    )
    rows.append(
        StartupChecklistRow(
            item="Output boundary",
            status="ok",
            detail="Dashboard outputs are research signals only, not financial advice or buy/sell recommendations.",
        )
    )
    return rows


def startup_checklist_has_blockers(rows: list[StartupChecklistRow]) -> bool:
    """Return whether any startup checklist row blocks configured loading."""
    return any(row.status == "blocker" for row in rows)


def run_yahoo_historical_smoke_test(adapter) -> YahooSmokeTestResult:
    """Run one cache-first Yahoo historical loading smoke test through an adapter."""
    before = adapter.cache_metadata()
    try:
        prices = adapter.load_prices(force_refresh=False)
        after = adapter.cache_metadata()
        start_date, end_date = _date_range(prices)
        return YahooSmokeTestResult(
            attempted_tickers=tuple(adapter.tickers),
            rows_loaded=int(len(prices)),
            start_date=start_date,
            end_date=end_date,
            cache_path=str(after.get("cache_path") or before.get("cache_path") or ""),
            cache_exists_before=bool(before.get("cache_exists")),
            cache_exists_after=bool(after.get("cache_exists")),
            cache_status=_smoke_cache_status(before, after, getattr(adapter, "warnings", [])),
            warnings=tuple(getattr(adapter, "warnings", [])),
        )
    except Exception as exc:
        after = adapter.cache_metadata()
        return YahooSmokeTestResult(
            attempted_tickers=tuple(getattr(adapter, "tickers", [])),
            rows_loaded=0,
            start_date="",
            end_date="",
            cache_path=str(after.get("cache_path") or before.get("cache_path") or ""),
            cache_exists_before=bool(before.get("cache_exists")),
            cache_exists_after=bool(after.get("cache_exists")),
            cache_status=_smoke_cache_status(before, after, getattr(adapter, "warnings", [])),
            warnings=tuple(getattr(adapter, "warnings", [])),
            error=str(exc),
        )


def _reference_checklist_rows(reference_data: dict, demo_reference_enabled: bool) -> list[StartupChecklistRow]:
    required = {
        "metadata_path": "metadata",
        "sector_map_path": "sector map",
        "country_map_path": "country map",
    }
    optional = {
        "asset_map_path": "asset map",
        "dr_mapping_path": "DR mapping",
        "thailand_universe_path": "Thailand universe",
        "thailand_sector_map_path": "Thailand sector map",
        "thailand_security_types_path": "Thailand security types",
        "thailand_liquidity_path": "Thailand liquidity",
        "thailand_dr_mapping_path": "Thailand DR/DRx mapping",
        "dr_market_data_path": "DR market data",
        "dr_bid_ask_path": "DR bid/ask",
        "dr_fair_value_inputs_path": "DR fair-value inputs",
        "fx_rates_path": "FX rates",
        "underlying_prices_path": "underlying prices",
    }
    rows: list[StartupChecklistRow] = []
    missing_required: list[str] = []
    present_required: list[str] = []
    for key, label in required.items():
        path = reference_data.get(key)
        if path and Path(path).exists():
            present_required.append(label)
        else:
            missing_required.append(f"{label} ({path or 'not configured'})")
    rows.append(
        StartupChecklistRow(
            item="Required production references",
            status="ok" if not missing_required else ("warning" if demo_reference_enabled else "blocker"),
            detail=(
                f"Available: {', '.join(present_required)}. Missing: {', '.join(missing_required)}"
                if missing_required
                else f"Available: {', '.join(present_required)}"
            ),
            next_step=(
                "Provide verified local reference files or enable demo reference mode for smoke testing only."
                if missing_required and not demo_reference_enabled
                else ("Replace fake/sample references with verified local files before production research." if missing_required else "")
            ),
        )
    )

    missing_optional: list[str] = []
    present_optional: list[str] = []
    for key, label in optional.items():
        path = reference_data.get(key)
        if path and Path(path).exists():
            present_optional.append(label)
        else:
            missing_optional.append(label)
    rows.append(
        StartupChecklistRow(
            item="Optional local references",
            status="ok" if not missing_optional else "warning",
            detail=(
                f"Available: {len(present_optional)} optional reference(s). Missing or unavailable: {', '.join(missing_optional)}"
                if missing_optional
                else f"Available: {len(present_optional)} optional reference(s)."
            ),
            next_step="Optional DR/Thailand quality layers will be skipped or limited when local files are missing." if missing_optional else "",
        )
    )
    return rows


def _date_range(prices: pd.DataFrame) -> tuple[str, str]:
    if prices is None or prices.empty or "Date" not in prices.columns:
        return "", ""
    dates = pd.to_datetime(prices["Date"], errors="coerce").dropna()
    if dates.empty:
        return "", ""
    return dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d")


def _smoke_cache_status(before: dict[str, Any], after: dict[str, Any], warnings: list[str]) -> str:
    if any("fallback to cache" in warning for warning in warnings):
        return "fallback_to_cache"
    if before.get("cache_exists"):
        return "cache_hit_or_refresh"
    if after.get("cache_exists"):
        return "cache_created"
    return "cache_miss"
