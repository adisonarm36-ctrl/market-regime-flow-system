from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import streamlit as st

from src.backtest import BacktestConfig
from src.config_validation import (
    DEMO_REFERENCE_MODE_WARNING,
    DEMO_REFERENCE_PATHS,
    apply_demo_reference_mode,
    validate_data_sources_config,
    validate_metadata_schema,
)
from src.config_loader import load_yaml
from src.data_adapters import get_data_adapter
from src.data_adapters.csv_adapter import CsvDataAdapter
from src.data_adapters.yahoo_adapter import YahooDataAdapter
from src.data_loader import pivot_prices, pivot_volume
from src.dashboard_components import badge_list_markdown, render_dataframe, render_empty_state
from src.report_generator import build_daily_report
from src.startup_diagnostics import (
    StartupChecklistRow,
    ProductionReferenceReadinessRow,
    YahooSmokeTestResult,
    build_yahoo_startup_checklist,
    build_production_reference_readiness,
    check_yfinance_available,
    run_yahoo_historical_smoke_test,
    startup_checklist_has_blockers,
    summarize_yahoo_smoke_test_state,
    summarize_yahoo_startup_state,
    yfinance_missing_guidance,
)
from src.topdown_pipeline import run_pipeline_from_config, run_topdown_pipeline
from src.thailand_reference import load_thailand_liquidity, load_thailand_universe
from src.yahoo_universe import build_thailand_domestic_yahoo_ticker_universe


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"
CONFIG_SOURCE_MODE = "Config source"
MANUAL_FALLBACK_MODE = "Advanced / fallback manual upload"
TODAY_DECISION_HUB_PAGE = "Today Decision Hub"


def _read_csv_upload(uploaded_file) -> pd.DataFrame | None:
    if uploaded_file is None:
        return None
    df = pd.read_csv(uploaded_file)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    return df


def dashboard_source_options() -> list[str]:
    """Return dashboard source choices with config/Yahoo first."""
    return [CONFIG_SOURCE_MODE, MANUAL_FALLBACK_MODE]


def active_source_label(config: dict | None) -> str:
    """Return a user-facing active source label from data_sources.yaml."""
    if not config:
        return "active_source: unavailable"
    return f"active_source: {config.get('active_source', 'csv')}"


def yahoo_cache_status(adapter: YahooDataAdapter) -> dict[str, object]:
    """Return report-ready Yahoo cache status without loading data."""
    return adapter.cache_metadata()


def apply_yahoo_runtime_options(config: dict, fallback_to_cache: bool, force_refresh: bool = False) -> dict:
    """Apply dashboard Yahoo runtime options without mutating loaded config."""
    result = deepcopy(config)
    yahoo_settings = result.setdefault("source_settings", {}).setdefault("yahoo", {})
    yahoo_settings["fallback_to_cache"] = bool(fallback_to_cache)
    yahoo_settings["force_refresh"] = bool(force_refresh)
    return result


def apply_yahoo_ticker_universe(config: dict, yahoo_tickers: list[str]) -> dict:
    """Apply a locally generated Yahoo ticker universe without mutating config."""
    result = deepcopy(config)
    result.setdefault("source_settings", {}).setdefault("yahoo", {})["tickers"] = list(yahoo_tickers)
    return result


def yahoo_cache_token(adapter: YahooDataAdapter) -> str:
    """Return a cache token that changes when the Yahoo cache file is updated."""
    cache_path = adapter.cache_path()
    if not cache_path.exists():
        return ""
    return str(cache_path.stat().st_mtime_ns)


def disable_yahoo_force_refresh(config: dict) -> dict:
    """Return a config copy that keeps Yahoo fallback options but restores cache-first loading."""
    result = deepcopy(config)
    yahoo_settings = result.setdefault("source_settings", {}).setdefault("yahoo", {})
    yahoo_settings["force_refresh"] = False
    return result


def apply_demo_reference_runtime_config(config: dict, enabled: bool) -> tuple[dict, list[str]]:
    """Apply demo reference paths to a runtime config copy when explicitly enabled."""
    if not enabled:
        return deepcopy(config), []
    return apply_demo_reference_mode(config)


def should_enable_demo_reference_by_default(config: dict | None) -> bool:
    """Return whether first-run config should default to bundled demo references."""
    if not config or config.get("active_source") != "yahoo":
        return False
    reference_data = config.get("source_settings", {}).get("yahoo", {}).get("reference_data", {}) or {}
    required_keys = ["metadata_path", "sector_map_path", "country_map_path"]
    missing_required = any(not reference_data.get(key) or not Path(reference_data[key]).exists() for key in required_keys)
    demo_ready = all(Path(DEMO_REFERENCE_PATHS[key]).exists() for key in [*required_keys, "asset_map_path"])
    return missing_required and demo_ready


def yahoo_dependency_diagnostic(find_spec=None):
    """Return yfinance availability for the active dashboard Python runtime."""
    return check_yfinance_available() if find_spec is None else check_yfinance_available(find_spec=find_spec)


def _safe_get_data_adapter(config: dict):
    try:
        return get_data_adapter(config)
    except Exception as exc:
        return exc


def main() -> None:
    """Run the Streamlit research dashboard."""
    st.set_page_config(page_title="Market Regime Flow System", layout="wide")
    st.title("Market Regime Flow System")
    st.caption("Research signals only. No financial advice or guaranteed buy/sell recommendations.")
    st.info("Use verified CSV data for research. Bundled sample data is fake/demo data for smoke testing only.")
    config = _load_dashboard_config()

    with st.sidebar:
        st.header("Data Source")
        st.caption("Default path: configured historical source. Manual CSV upload is an advanced fallback.")
        st.write(active_source_label(config))
        use_demo_reference_data = False
        demo_reference_warnings: list[str] = []
        if config is not None:
            default_demo_reference_data = should_enable_demo_reference_by_default(config)
            use_demo_reference_data = st.checkbox(
                "Use bundled fake/demo reference files",
                value=default_demo_reference_data,
                help="Maps missing local reference paths to bundled fake/sample files for first-run smoke testing only.",
            )
            if use_demo_reference_data:
                st.warning(DEMO_REFERENCE_MODE_WARNING)
                st.caption("Production reference paths remain configured in data_sources.yaml; demo mode only changes this dashboard run.")
            if default_demo_reference_data:
                st.caption("Enabled by default because production metadata, sector, or country references are missing.")
        if config is not None:
            _show_config_validation_warnings(validate_data_sources_config(config))
        data_mode = st.radio("Data mode", dashboard_source_options(), index=0)
        use_sample_data = False
        ohlcv_upload = metadata_upload = country_upload = asset_upload = None
        thailand_upload = dr_mapping_upload = dr_ohlcv_upload = None
        if data_mode == MANUAL_FALLBACK_MODE:
            with st.expander("Advanced / fallback manual upload", expanded=True):
                use_sample_data = st.checkbox("Use bundled fake/demo sample data", value=False)
                st.markdown(
                    "Required OHLCV columns: `Date,Ticker,Open,High,Low,Close,Volume`. "
                    "Optional: `Adjusted Close`. Metadata sample columns are documented in README."
                )
                ohlcv_upload = st.file_uploader("OHLCV CSV", type=["csv"])
                metadata_upload = st.file_uploader("Metadata CSV", type=["csv"])
                country_upload = st.file_uploader("Country map CSV", type=["csv"])
                asset_upload = st.file_uploader("Asset map CSV", type=["csv"])
                thailand_upload = st.file_uploader("Thailand metadata CSV", type=["csv"])
                dr_mapping_upload = st.file_uploader("DR mapping CSV", type=["csv"])
                dr_ohlcv_upload = st.file_uploader("DR OHLCV CSV", type=["csv"])
        benchmark_ticker = st.text_input("Benchmark ticker", value="")
        enable_backtest = st.checkbox("Enable research backtest assumptions", value=False)
        backtest_config = _sidebar_backtest_config(enable_backtest)
        yahoo_fallback_to_cache = True
        yahoo_universe_source = "Configured Yahoo tickers"
        selected_thailand_universe = "SET ex-DR"

    if data_mode == CONFIG_SOURCE_MODE:
        if config is None:
            st.error("Could not load config/data_sources.yaml. Use Advanced / fallback manual upload if needed.")
            return
        runtime_config, demo_reference_warnings = apply_demo_reference_runtime_config(config, use_demo_reference_data)
        dashboard_cache_status: dict[str, object] | None = None
        if use_demo_reference_data:
            st.success("Demo mode is enabled for smoke testing. Not production-ready.")
            st.caption("Bundled reference files are fake/sample-only; replace them with verified local files before research use.")
        for warning in demo_reference_warnings:
            st.caption(warning)
        production_readiness_rows = build_production_reference_readiness(config)
        _show_production_reference_readiness(production_readiness_rows, demo_reference_enabled=use_demo_reference_data)
        adapter = _safe_get_data_adapter(runtime_config)
        adapter_error = None
        if isinstance(adapter, Exception):
            adapter_error = str(adapter)
            adapter = None
        if isinstance(adapter, YahooDataAdapter):
            st.sidebar.info("Yahoo mode uses historical yfinance data only. It is not realtime.")
            yahoo_dependency = yahoo_dependency_diagnostic()
            if yahoo_dependency.importable:
                st.sidebar.success(yahoo_dependency.summary)
            else:
                st.sidebar.error(yahoo_dependency.summary)
            yahoo_universe_source = st.sidebar.selectbox(
                "Yahoo ticker universe",
                ["Configured Yahoo tickers", "Local Thailand domestic universe"],
            )
            if yahoo_universe_source == "Local Thailand domestic universe":
                selected_thailand_universe = st.sidebar.selectbox("Thailand universe", ["SET ex-DR", "SET50", "SET100", "mai"])
            yahoo_fallback_to_cache = st.sidebar.checkbox("Fallback to stale cache if Yahoo fetch fails", value=adapter.fallback_to_cache)
            yahoo_refresh_requested = st.sidebar.button("Refresh Yahoo historical data")
            runtime_config = apply_yahoo_runtime_options(
                runtime_config,
                fallback_to_cache=yahoo_fallback_to_cache,
                force_refresh=yahoo_refresh_requested,
            )
            if yahoo_universe_source == "Local Thailand domestic universe":
                runtime_config = _apply_local_thailand_yahoo_universe(runtime_config, selected_thailand_universe)
            adapter = get_data_adapter(runtime_config)
            cache_status = yahoo_cache_status(adapter)
            dashboard_cache_status = cache_status
            st.sidebar.write(
                {
                    "tickers": adapter.tickers,
                    "period": adapter.period,
                    "start": adapter.start,
                    "end": adapter.end,
                    "interval": adapter.interval,
                    "cache_dir": str(adapter.cache_dir),
                    "cache_ttl_hours": adapter.cache_ttl_hours,
                    "fallback_to_cache": adapter.fallback_to_cache,
                    "cache_first": cache_status["cache_first_enabled"],
                }
            )
            st.sidebar.write(f"Cache path: `{cache_status['cache_path']}`")
            if cache_status["cache_first_enabled"]:
                st.sidebar.success("Cache-first mode is active. Reruns use fresh cache before downloading.")
            else:
                st.sidebar.warning("Refresh requested. This run will attempt a historical Yahoo download.")
            if cache_status["cache_exists"]:
                st.sidebar.success("Yahoo cache file is available.")
                st.sidebar.write(f"Cache last updated: `{cache_status['cache_last_updated']}`")
                if cache_status["cache_is_stale"]:
                    st.sidebar.warning("Yahoo cache is stale based on configured cache_ttl_hours.")
            else:
                st.sidebar.warning("Yahoo cache file is not available yet.")
            yahoo_cache_marker = yahoo_cache_token(adapter)
            startup_rows = build_yahoo_startup_checklist(
                config,
                yfinance_diagnostic=yahoo_dependency,
                cache_status=cache_status,
                demo_reference_enabled=use_demo_reference_data,
                manual_upload_available=True,
                adapter_error=adapter_error,
            )
            _show_startup_checklist(startup_rows)
            _show_yahoo_startup_state(startup_rows, use_demo_reference_data)
            _show_yahoo_smoke_test_control(pipeline_config=disable_yahoo_force_refresh(runtime_config), startup_rows=startup_rows)
            if startup_checklist_has_blockers(startup_rows):
                st.error("Blocked: selected Yahoo runtime configuration cannot run. Resolve the hard blocker or use Advanced / fallback manual upload.")
                return
        elif runtime_config.get("active_source") == "yahoo":
            yahoo_dependency = yahoo_dependency_diagnostic()
            startup_rows = build_yahoo_startup_checklist(
                config,
                yfinance_diagnostic=yahoo_dependency,
                demo_reference_enabled=use_demo_reference_data,
                manual_upload_available=True,
                adapter_error=adapter_error,
            )
            _show_startup_checklist(startup_rows)
            _show_yahoo_startup_state(startup_rows, use_demo_reference_data)
            st.error("Blocked: selected Yahoo runtime configuration cannot run. Resolve the hard blocker or use Advanced / fallback manual upload.")
            return
        else:
            yahoo_refresh_requested = False
            yahoo_cache_marker = ""
        try:
            ohlcv, adapter_warnings = _load_prices_once(runtime_config, yahoo_refresh_requested, yahoo_cache_marker)
        except Exception as exc:
            st.error(f"Could not load configured data source: {exc}")
            return
        for warning in adapter_warnings:
            st.warning(warning)
        metadata = _safe_adapter_load(adapter.load_metadata, "metadata")
        asset_map = _safe_adapter_load(adapter.load_sector_map, "sector/asset map")
        dr_mapping = _safe_adapter_load(adapter.load_dr_mapping, "DR mapping")
        country_map = None
        thailand_metadata = None
        dr_ohlcv = None
    elif use_sample_data:
        sample_adapter = CsvDataAdapter(
            price_path=SAMPLE_DIR / "prices_sample.csv",
            metadata_path=SAMPLE_DIR / "metadata_sample.csv",
            sector_map_path=SAMPLE_DIR / "asset_map_sample.csv",
            dr_mapping_path=SAMPLE_DIR / "dr_mapping_sample.csv",
        )
        ohlcv = sample_adapter.load_prices()
        metadata = sample_adapter.load_metadata()
        asset_map = sample_adapter.load_sector_map()
        dr_mapping = sample_adapter.load_dr_mapping()
        country_map = None
        thailand_metadata = None
        dr_ohlcv = ohlcv[ohlcv["Ticker"].isin(dr_mapping["DR_Ticker"])] if not dr_mapping.empty else None
        st.sidebar.success("Loaded fake/demo sample data from data/sample.")
    else:
        ohlcv = _read_csv_upload(ohlcv_upload)
        metadata = _read_csv_upload(metadata_upload)
        country_map = _read_csv_upload(country_upload)
        asset_map = _read_csv_upload(asset_upload)
        thailand_metadata = _read_csv_upload(thailand_upload)
        dr_mapping = _read_csv_upload(dr_mapping_upload)
        dr_ohlcv = _read_csv_upload(dr_ohlcv_upload)

    if ohlcv is None:
        st.warning("Upload an OHLCV CSV or enable bundled fake/demo sample data to run the dashboard.")
        return

    try:
        price_df = pivot_prices(ohlcv)
        volume_df = pivot_volume(ohlcv)
    except Exception as exc:
        st.error(f"Could not load OHLCV data: {exc}")
        return

    dr_prices = pivot_prices(dr_ohlcv) if dr_ohlcv is not None else None
    dr_volume = pivot_volume(dr_ohlcv) if dr_ohlcv is not None else None
    if metadata is None:
        st.warning("Metadata CSV is missing. Country, sector, Thailand breadth, and stock ranking layers will be limited.")
    else:
        for warning in validate_metadata_schema(metadata):
            st.warning(warning)
    if dr_mapping is None:
        st.warning("DR mapping is missing. DR execution quality will be skipped and reported as missing optional data.")

    if data_mode == CONFIG_SOURCE_MODE:
        if isinstance(adapter, YahooDataAdapter):
            pipeline_config = disable_yahoo_force_refresh(runtime_config)
            yahoo_cache_marker = yahoo_cache_token(get_data_adapter(pipeline_config))
        else:
            pipeline_config = runtime_config
        outputs = _run_config_pipeline_once(pipeline_config, enable_backtest, backtest_config, False, yahoo_cache_marker)
        _show_demo_run_summary(outputs, use_demo_reference_data, production_readiness_rows)
        _show_status_tables(outputs)
    else:
        outputs = run_topdown_pipeline(
            price_df=price_df,
            volume_df=volume_df,
            metadata_df=metadata,
            asset_mapping_df=asset_map,
            country_map_df=country_map,
            thailand_metadata_df=thailand_metadata,
            dr_mapping_df=dr_mapping,
            dr_price_df=dr_prices,
            dr_volume_df=dr_volume,
            benchmark_ticker=benchmark_ticker or None,
            backtest_enabled=enable_backtest,
            backtest_config=backtest_config,
        )

    pages = [
        TODAY_DECISION_HUB_PAGE,
        "Global Flow Map",
        "Country Market Health",
        "Thailand Market Health",
        "Thailand Reference Status",
        "Sector Breadth",
        "Theme / Correlation Cluster",
        "Stock Ranking",
        "DR Global Proxy",
        "Redundancy Report",
        "Backtest",
        "Daily Report",
    ]
    page = st.sidebar.radio("Page", pages)

    if page == TODAY_DECISION_HUB_PAGE:
        _show_today_decision_hub(
            outputs,
            source_label=active_source_label(config) if data_mode == CONFIG_SOURCE_MODE else "active_source: manual upload",
            demo_reference_enabled=bool(use_demo_reference_data),
            cache_status=dashboard_cache_status if data_mode == CONFIG_SOURCE_MODE else None,
        )
    elif page == "Global Flow Map":
        _show_table("Global Flow Summary", outputs.get("global_flow_summary"))
        _show_table("Asset Class Flow", outputs.get("asset_class_flow_summary"))
    elif page == "Country Market Health":
        _show_table("Country Breadth Summary", outputs.get("country_breadth_summary"))
    elif page == "Thailand Market Health":
        _show_table("Thailand Market Health", outputs.get("thailand_market_health"))
        _show_table("Thailand Domestic Breadth Eligibility", outputs.get("thailand_eligibility_report"))
        _show_table("Excluded Securities", outputs.get("thailand_excluded_securities", outputs.get("excluded_summary")))
        st.caption("DR/DRx, DW, ETF, warrants, suspended, and failed-liquidity rows are excluded from Thailand domestic breadth.")
    elif page == "Thailand Reference Status":
        st.info("Thailand reference sample files are fake/demo data only. Replace them with verified local CSV/YAML files for research.")
        _show_table("Thailand Reference Status", outputs.get("thailand_reference_report"))
        _show_table("Thailand Domestic Breadth Eligibility", outputs.get("thailand_eligibility_report"))
        _show_table("Thailand DR / DRx Reference", outputs.get("thailand_dr_mapping_report"))
        _show_table("Duplicate DR Underlying Groups", outputs.get("dr_duplicate_underlying_report"))
    elif page == "Sector Breadth":
        _show_table("Sector Breadth Summary", outputs.get("sector_breadth_summary"))
    elif page == "Theme / Correlation Cluster":
        _show_table("Cluster Summary", outputs.get("cluster_summary"))
        _show_table("Cluster Members", outputs.get("cluster_membership"))
        _show_table("Redundant Instruments", outputs.get("redundancy_report"))
    elif page == "Stock Ranking":
        _show_signal_browser(outputs.get("stock_ranking"))
    elif page == "DR Global Proxy":
        st.warning("⚠️ **RESEARCH SIGNALS ONLY**: The metrics, rankings, and indicators presented below are purely for research and quantitative signal screening. They do NOT constitute financial advice or investment recommendations. DRs and underlying foreign proxies carry FX, tracking, and liquidity risk.")
        
        tabs = st.tabs([
            "Execution Ready Rankings",
            "Fair Value & Premium/Discount",
            "Tracking & FX-Adjusted Returns",
            "Liquidity Details",
            "Quality Warnings"
        ])
        
        with tabs[0]:
            _show_table("Execution Ready Rankings", outputs.get("dr_execution_quality_report"))
        with tabs[1]:
            _show_table("Fair Value & Premium/Discount", outputs.get("dr_fair_value_report"))
        with tabs[2]:
            _show_table("Tracking & FX-Adjusted Returns", outputs.get("dr_tracking_report"))
        with tabs[3]:
            _show_table("Liquidity Details", outputs.get("dr_liquidity_report"))
        with tabs[4]:
            _show_table("Quality Warnings", outputs.get("dr_quality_warnings"))
            
        st.markdown("---")
        _show_table("Thailand DR / DRx Reference Status", outputs.get("thailand_dr_mapping_report"))
        _show_table("Duplicate DR Underlying Groups", outputs.get("dr_duplicate_underlying_report"))
    elif page == "Redundancy Report":
        _show_table("Redundant Instruments", outputs.get("redundancy_report"))
    elif page == "Backtest":
        _show_backtest_page(outputs)
    elif page == "Daily Report":
        report = build_daily_report(outputs)
        for title, text in report.items():
            st.subheader(title.replace("_", " ").title())
            st.write(text)


def _show_table(title: str, table: pd.DataFrame | None) -> None:
    st.subheader(title)
    if table is None or table.empty:
        render_empty_state(st, "No data available for this layer. Missing data is skipped.")
        return
    render_dataframe(st, table)


def build_today_decision_hub_tables(
    outputs: dict[str, pd.DataFrame],
    source_label: str = "",
    demo_reference_enabled: bool = False,
    cache_status: dict[str, object] | None = None,
) -> dict[str, pd.DataFrame]:
    """Build presentation tables for the Today Decision Hub from existing outputs only."""
    return {
        "Market Regime": _build_market_regime_rows(outputs),
        "Top Signals": _build_top_signal_rows(outputs.get("stock_ranking", pd.DataFrame())),
        "Risk Alerts": _build_risk_alert_rows(outputs),
        "Strategy Health": _build_strategy_health_rows(outputs),
        "Data Freshness": _build_data_freshness_rows(source_label, demo_reference_enabled, cache_status),
        "Quick Actions": _build_quick_action_rows(outputs),
    }


def _show_today_decision_hub(
    outputs: dict[str, pd.DataFrame],
    source_label: str = "",
    demo_reference_enabled: bool = False,
    cache_status: dict[str, object] | None = None,
) -> None:
    st.subheader("Today Decision Hub")
    st.caption("Research signals only. This page summarizes existing outputs and does not change calculations.")
    tables = build_today_decision_hub_tables(outputs, source_label, demo_reference_enabled, cache_status)

    left, right = st.columns(2)
    with left:
        _show_hub_table(
            "Market Regime",
            tables["Market Regime"],
            "Market regime not available. Needs price data and breadth inputs.",
        )
        _show_hub_table(
            "Risk Alerts",
            tables["Risk Alerts"],
            "No warnings reported by current outputs.",
        )
        _show_hub_table(
            "Data Freshness",
            tables["Data Freshness"],
            "Freshness unavailable. Needs loaded price data or cache metadata.",
        )
    with right:
        _show_hub_table(
            "Top Signals",
            tables["Top Signals"],
            "No research candidates available. Needs metadata, momentum, and ranking outputs.",
        )
        _show_hub_table(
            "Strategy Health",
            tables["Strategy Health"],
            "Strategy health unavailable until pipeline outputs exist.",
        )
        _show_hub_table(
            "Quick Actions",
            tables["Quick Actions"],
            "Actions unavailable until data source is configured or uploaded.",
        )

    with st.expander("Raw supporting outputs", expanded=False):
        _show_table("Global Flow Summary", outputs.get("global_flow_summary"))
        _show_table("Country Breadth Summary", outputs.get("country_breadth_summary"))
        _show_table("Thailand Market Health", outputs.get("thailand_market_health"))
        _show_table("Sector Breadth Summary", outputs.get("sector_breadth_summary"))
        _show_table("Ranked Research Candidates", outputs.get("stock_ranking"))
        _show_table("Pipeline Warnings", outputs.get("warnings"))


def _show_hub_table(title: str, table: pd.DataFrame, empty_message: str) -> None:
    st.markdown(f"### {title}")
    if table.empty:
        render_empty_state(st, empty_message, action="Inspect source settings, warnings, or raw supporting outputs.")
        return
    render_dataframe(st, table)


def _build_market_regime_rows(outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    country = _sort_by_existing_score(outputs.get("country_breadth_summary"), "breadth_score")
    if not country.empty:
        row = country.iloc[0]
        rows.append(
            {
                "section": "Country market health",
                "signal": _safe_row_text(row, "regime"),
                "metric": _safe_numeric_text(row, "breadth_score"),
                "detail": f"{_safe_row_text(row, 'country')} breadth_score",
                "source": "country_breadth_summary",
            }
        )
    thailand = _sort_by_existing_score(outputs.get("thailand_market_health"), "breadth_score")
    if not thailand.empty:
        row = thailand.iloc[0]
        rows.append(
            {
                "section": "Thailand market health",
                "signal": _safe_row_text(row, "regime"),
                "metric": _safe_numeric_text(row, "breadth_score"),
                "detail": f"{_safe_row_text(row, 'universe')} breadth_score",
                "source": "thailand_market_health",
            }
        )
    flow = _sort_by_existing_score(outputs.get("global_flow_summary"), "flow_score")
    if not flow.empty:
        row = flow.iloc[0]
        rows.append(
            {
                "section": "Global flow proxy",
                "signal": _safe_row_text(row, "flow_classification"),
                "metric": _safe_numeric_text(row, "flow_score"),
                "detail": f"{_safe_row_text(row, 'Ticker')} flow signal proxy",
                "source": "global_flow_summary",
            }
        )
    sector = _sort_by_existing_score(outputs.get("sector_breadth_summary"), "breadth_score")
    if not sector.empty:
        row = sector.iloc[0]
        rows.append(
            {
                "section": "Sector breadth",
                "signal": _safe_row_text(row, "regime"),
                "metric": _safe_numeric_text(row, "breadth_score"),
                "detail": f"{_safe_row_text(row, 'Sector')} breadth_score",
                "source": "sector_breadth_summary",
            }
        )
    return pd.DataFrame(rows)


def _build_top_signal_rows(stock_ranking: pd.DataFrame | None, limit: int = 5) -> pd.DataFrame:
    if stock_ranking is None or stock_ranking.empty or "Ticker" not in stock_ranking.columns:
        return pd.DataFrame()
    ranking = _sort_by_existing_score(stock_ranking, "research_score").head(limit)
    rows = []
    for _, row in ranking.iterrows():
        rows.append(
            {
                "Ticker": _safe_row_text(row, "Ticker"),
                "research_score": _safe_numeric_text(row, "research_score"),
                "signal_type": _safe_row_text(row, "signal_type"),
                "country": _safe_row_text(row, "Country"),
                "sector": _safe_row_text(row, "Sector"),
                "reason": _safe_row_text(row, "reason"),
                "warnings": _combine_row_warnings(row, ["failed_filters", "data_quality_warning", "dr_data_quality_warning"]),
            }
        )
    return pd.DataFrame(rows)


def _build_risk_alert_rows(outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sources = [
        ("Pipeline", outputs.get("warnings"), "warning"),
        ("Backtest", outputs.get("backtest_warnings"), "warning"),
        ("DR quality", outputs.get("dr_quality_warnings"), "warning"),
    ]
    rows: list[dict[str, object]] = []
    for category, table, column in sources:
        if not isinstance(table, pd.DataFrame) or table.empty or column not in table.columns:
            continue
        for value in table[column].dropna().astype(str).head(5):
            rows.append({"category": category, "status": "warning", "detail": value})
    return pd.DataFrame(rows)


def _build_strategy_health_rows(outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    layer_sources = [
        ("Global flow", "global_flow_summary"),
        ("Country breadth", "country_breadth_summary"),
        ("Thailand market health", "thailand_market_health"),
        ("Sector breadth", "sector_breadth_summary"),
        ("Theme clusters", "cluster_summary"),
        ("Research candidates", "stock_ranking"),
        ("Redundancy report", "redundancy_report"),
        ("Backtest assumptions", "backtest_summary"),
    ]
    rows = []
    for layer, key in layer_sources:
        count = _row_count(outputs.get(key))
        rows.append(
            {
                "layer": layer,
                "status": "available" if count else "skipped",
                "rows": count,
                "source": key,
            }
        )
    return pd.DataFrame(rows)


def _build_data_freshness_rows(
    source_label: str,
    demo_reference_enabled: bool,
    cache_status: dict[str, object] | None,
) -> pd.DataFrame:
    rows = [
        {
            "item": "Source mode",
            "status": "available" if source_label else "missing",
            "detail": source_label or "Not available",
        },
        {
            "item": "Demo reference mode",
            "status": "warning" if demo_reference_enabled else "ok",
            "detail": "Enabled; fake/sample-only" if demo_reference_enabled else "Disabled",
        },
        {
            "item": "Yahoo data policy",
            "status": "info",
            "detail": "Historical/cache-based only; not realtime",
        },
    ]
    if cache_status:
        rows.extend(
            [
                {
                    "item": "Yahoo cache file",
                    "status": "available" if cache_status.get("cache_exists") else "missing",
                    "detail": str(cache_status.get("cache_path", "Not available")),
                },
                {
                    "item": "Yahoo cache freshness",
                    "status": "warning" if cache_status.get("cache_is_stale") else "ok",
                    "detail": str(cache_status.get("cache_last_updated", "Not available")),
                },
            ]
        )
    return pd.DataFrame(rows)


def _build_quick_action_rows(outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    stock_count = _row_count(outputs.get("stock_ranking"))
    warning_count = _row_count(outputs.get("warnings")) + _row_count(outputs.get("backtest_warnings"))
    report_ready = any(_row_count(outputs.get(key)) for key in ["global_flow_summary", "country_breadth_summary", "stock_ranking"])
    return pd.DataFrame(
        [
            {
                "action": "Review top research signals",
                "target": "Stock Ranking",
                "status": "available" if stock_count else "missing",
                "detail": f"{stock_count} ranked candidate row(s)",
            },
            {
                "action": "Inspect data-quality warnings",
                "target": "Data Source Status",
                "status": "warning" if warning_count else "ok",
                "detail": f"{warning_count} warning row(s)",
            },
            {
                "action": "Review narrative report",
                "target": "Daily Report",
                "status": "available" if report_ready else "missing",
                "detail": "CSV and HTML export helpers remain unchanged",
            },
        ]
    )


def _sort_by_existing_score(table: pd.DataFrame | None, score_column: str) -> pd.DataFrame:
    if table is None or table.empty:
        return pd.DataFrame()
    result = table.copy()
    if score_column in result.columns:
        result["_sort_score"] = pd.to_numeric(result[score_column], errors="coerce")
        result = result.sort_values("_sort_score", ascending=False, na_position="last").drop(columns=["_sort_score"])
    return result.reset_index(drop=True)


def _safe_row_text(row: pd.Series, column: str, fallback: str = "Not available") -> str:
    if column not in row.index:
        return fallback
    value = row.get(column)
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _safe_numeric_text(row: pd.Series, column: str, fallback: str = "Not available") -> str:
    if column not in row.index:
        return fallback
    value = pd.to_numeric(row.get(column), errors="coerce")
    if pd.isna(value):
        return fallback
    return f"{float(value):.2f}"


def _combine_row_warnings(row: pd.Series, columns: list[str]) -> str:
    values = []
    for column in columns:
        if column not in row.index:
            continue
        value = row.get(column)
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text:
            values.append(text)
    return "; ".join(values) if values else "None reported"


def build_signal_filter_options(stock_ranking: pd.DataFrame | None) -> dict[str, list[str]]:
    """Return available signal-browser filter values without changing source rows."""
    if stock_ranking is None or stock_ranking.empty:
        return {
            "countries": [],
            "sectors": [],
            "signal_types": [],
            "data_quality": [],
            "failed_filter_states": [],
        }
    result = {
        "countries": _unique_existing_values(stock_ranking, "Country"),
        "sectors": _unique_existing_values(stock_ranking, "Sector"),
        "signal_types": _unique_existing_values(stock_ranking, "signal_type"),
        "data_quality": [],
        "failed_filter_states": [],
    }
    quality_labels = [_signal_quality_label(row) for _, row in stock_ranking.iterrows()]
    failed_labels = [_signal_failed_filter_label(row) for _, row in stock_ranking.iterrows()]
    result["data_quality"] = sorted(set(quality_labels))
    result["failed_filter_states"] = sorted(set(failed_labels))
    return result


def filter_signal_ranking(
    stock_ranking: pd.DataFrame | None,
    countries: list[str] | None = None,
    sectors: list[str] | None = None,
    signal_types: list[str] | None = None,
    data_quality: list[str] | None = None,
    failed_filter_states: list[str] | None = None,
    sort_by: str = "research_score",
    ascending: bool = False,
) -> pd.DataFrame:
    """Return a filtered and sorted copy of stock ranking rows for presentation only."""
    if stock_ranking is None or stock_ranking.empty:
        return pd.DataFrame()
    result = stock_ranking.copy()
    result = _filter_by_values(result, "Country", countries)
    result = _filter_by_values(result, "Sector", sectors)
    result = _filter_by_values(result, "signal_type", signal_types)
    if data_quality:
        quality = result.apply(_signal_quality_label, axis=1)
        result = result[quality.isin(data_quality)]
    if failed_filter_states:
        failed = result.apply(_signal_failed_filter_label, axis=1)
        result = result[failed.isin(failed_filter_states)]
    if sort_by in result.columns:
        sortable = pd.to_numeric(result[sort_by], errors="coerce")
        result = result.assign(_sort_value=sortable).sort_values("_sort_value", ascending=ascending, na_position="last").drop(columns=["_sort_value"])
    elif "Ticker" in result.columns:
        result = result.sort_values("Ticker", ascending=True, na_position="last")
    return result.reset_index(drop=True)


def build_signal_card_rows(stock_ranking: pd.DataFrame | None, limit: int | None = None) -> pd.DataFrame:
    """Build scan-friendly signal card rows from existing stock-ranking columns."""
    if stock_ranking is None or stock_ranking.empty or "Ticker" not in stock_ranking.columns:
        return pd.DataFrame()
    source = stock_ranking.head(limit) if limit else stock_ranking
    rows = []
    for _, row in source.iterrows():
        rows.append(
            {
                "Ticker": _safe_row_text(row, "Ticker"),
                "badges": _signal_badge_text(row),
                "score": _safe_numeric_text(row, "research_score"),
                "momentum_score": _safe_numeric_text(row, "momentum_score"),
                "trend_quality": _safe_row_text(row, "trend_quality"),
                "country": _safe_row_text(row, "Country"),
                "sector": _safe_row_text(row, "Sector"),
                "industry": _safe_row_text(row, "Industry"),
                "signal_type": _safe_row_text(row, "signal_type"),
                "why": _safe_row_text(row, "reason"),
                "warnings": _combine_row_warnings(row, ["failed_filters", "data_quality_warning", "dr_data_quality_warning"]),
                "detail_sections": build_signal_detail_sections(row),
            }
        )
    return pd.DataFrame(rows)


def build_signal_detail_sections(row: pd.Series) -> dict[str, pd.DataFrame]:
    """Build fact/assumption/warning detail sections for one signal from existing row values."""
    fact_rows = _signal_detail_rows(
        row,
        [
            ("Ticker", "Ticker"),
            ("Security type", "SecurityType"),
            ("Country", "Country"),
            ("Sector", "Sector"),
            ("Industry", "Industry"),
            ("Universe", "Universe"),
            ("Signal type", "signal_type"),
            ("Research score", "research_score"),
            ("Momentum score", "momentum_score"),
            ("1M momentum", "momentum_1m"),
            ("3M momentum", "momentum_3m"),
            ("6M momentum", "momentum_6m"),
            ("12M momentum", "momentum_12m"),
            ("Volatility-adjusted momentum", "volatility_adjusted_momentum"),
            ("Distance from 52-week high", "distance_from_52week_high"),
            ("Above 50-day moving average", "above_50ma"),
            ("Above 200-day moving average", "above_200ma"),
            ("Trend quality", "trend_quality"),
            ("Country breadth score", "country_breadth_score"),
            ("Country regime", "country_regime"),
            ("Sector breadth score", "sector_breadth_score"),
            ("Cluster", "cluster"),
            ("Cluster score", "cluster_score"),
            ("DR quality score", "dr_quality_score"),
            ("Average traded value 20D", "average_traded_value_20d"),
        ],
        source="stock_ranking",
    )
    assumption_rows = [
        {
            "item": "Calculation source",
            "value": "Existing stock_ranking output",
            "source": "stock_ranking",
            "note": "Presentation only; no signal calculation changed.",
        },
        {
            "item": "Price or indicator chart",
            "value": "Needs data source",
            "source": "Not available",
            "note": "No ticker-level price series is present in stock_ranking.",
        },
        {
            "item": "Backtest evidence",
            "value": "Not available",
            "source": "Phase 5",
            "note": "Backtest evidence UX is out of scope for this phase.",
        },
    ]
    warning_rows = _signal_warning_rows(row)
    data_quality_rows = _signal_data_quality_rows(row)
    return {
        "Facts": pd.DataFrame(fact_rows),
        "Assumptions": pd.DataFrame(assumption_rows),
        "Warnings": pd.DataFrame(warning_rows),
        "Data Quality": pd.DataFrame(data_quality_rows),
        "Supporting Row": _supporting_row_table(row),
    }


def _show_signal_browser(stock_ranking: pd.DataFrame | None) -> None:
    st.subheader("Signal Explorer")
    st.caption("Research signals only. Cards and filters use existing stock_ranking columns without changing ranking calculations.")
    if stock_ranking is None or stock_ranking.empty:
        render_empty_state(st, "No research candidates available. Needs metadata, momentum, and ranking outputs.")
        _show_table("Ranked Research Candidates", stock_ranking)
        return

    options = build_signal_filter_options(stock_ranking)
    with st.expander("Signal filters and sorting", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_countries = st.multiselect("Country", options["countries"])
            selected_sectors = st.multiselect("Sector", options["sectors"])
            selected_signal_types = st.multiselect("Signal type", options["signal_types"])
        with col2:
            selected_quality = st.multiselect("Data quality", options["data_quality"])
            selected_failed = st.multiselect("Failed-filter state", options["failed_filter_states"])
            sort_options = [column for column in ["research_score", "momentum_score", "country_breadth_score", "sector_breadth_score", "Ticker"] if column in stock_ranking.columns]
            sort_by = st.selectbox("Sort by", sort_options or ["Ticker"], index=0)
            sort_direction = st.radio("Sort direction", ["Descending", "Ascending"], horizontal=True)

    filtered = filter_signal_ranking(
        stock_ranking,
        countries=selected_countries,
        sectors=selected_sectors,
        signal_types=selected_signal_types,
        data_quality=selected_quality,
        failed_filter_states=selected_failed,
        sort_by=sort_by,
        ascending=sort_direction == "Ascending",
    )
    st.write(f"{len(filtered)} of {len(stock_ranking)} research candidate row(s) shown.")
    card_rows = build_signal_card_rows(filtered)
    if card_rows.empty:
        render_empty_state(st, "No research candidates match the selected filters.", action="Clear filters or inspect the raw ranking table.")
    else:
        for _, card in card_rows.iterrows():
            _render_signal_card(card)

    with st.expander("Raw stock_ranking table", expanded=False):
        _show_table("Ranked Research Candidates", stock_ranking)


def _render_signal_card(card: pd.Series) -> None:
    with st.container(border=True):
        st.markdown(f"### {card['Ticker']}")
        st.markdown(str(card["badges"]))
        cols = st.columns(3)
        cols[0].metric("Research score", str(card["score"]))
        cols[1].metric("Momentum score", str(card["momentum_score"]))
        cols[2].metric("Trend quality", str(card["trend_quality"]))
        st.write(
            {
                "country": card["country"],
                "sector": card["sector"],
                "industry": card["industry"],
                "signal_type": card["signal_type"],
            }
        )
        st.caption(f"Why this signal: {card['why']}")
        if card["warnings"] != "None reported":
            st.warning(f"Warnings: {card['warnings']}")
        detail_sections = card.get("detail_sections")
        if isinstance(detail_sections, dict):
            with st.expander(f"Signal detail for {card['Ticker']}", expanded=False):
                _show_signal_detail_sections(detail_sections)


def _show_signal_detail_sections(sections: dict[str, pd.DataFrame]) -> None:
    st.info("Signal detail uses existing output rows only. It is not financial advice and does not change calculations.")
    for section_name in ["Facts", "Assumptions", "Warnings", "Data Quality", "Supporting Row"]:
        table = sections.get(section_name, pd.DataFrame())
        st.markdown(f"#### {section_name}")
        if table.empty:
            render_empty_state(st, "No data available for this detail section.")
        else:
            render_dataframe(st, table)


def _unique_existing_values(table: pd.DataFrame, column: str) -> list[str]:
    if column not in table.columns:
        return []
    values = []
    for value in table[column].dropna().astype(str):
        text = value.strip()
        if text:
            values.append(text)
    return sorted(set(values))


def _filter_by_values(table: pd.DataFrame, column: str, selected: list[str] | None) -> pd.DataFrame:
    if not selected or column not in table.columns:
        return table
    values = table[column].fillna("").astype(str).str.strip()
    return table[values.isin(selected)]


def _signal_quality_label(row: pd.Series) -> str:
    warnings = _combine_row_warnings(row, ["data_quality_warning", "dr_data_quality_warning"])
    return "Warnings reported" if warnings != "None reported" else "No warnings reported"


def _signal_failed_filter_label(row: pd.Series) -> str:
    failed = _safe_row_text(row, "failed_filters", fallback="")
    return "Failed filters" if failed else "No failed filters"


def _signal_badge_text(row: pd.Series) -> str:
    badges: list[tuple[str, str]] = [("Research signal", "info")]
    security_type = _safe_row_text(row, "SecurityType", fallback="")
    if security_type.upper() in {"DR", "DRX"}:
        badges.append(("DR/DRx proxy", "warning"))
    if _signal_failed_filter_label(row) == "Failed filters":
        badges.append(("Failed filters", "warning"))
    if _signal_quality_label(row) == "Warnings reported":
        badges.append(("Low data confidence", "warning"))
    if _safe_row_text(row, "Sector", fallback=""):
        badges.append(("Sector context", "available"))
    if _safe_row_text(row, "trend_quality", fallback=""):
        badges.append(("Trend metric available", "available"))
    return badge_list_markdown(badges)


def _signal_detail_rows(row: pd.Series, fields: list[tuple[str, str]], source: str) -> list[dict[str, str]]:
    rows = []
    for label, column in fields:
        value = _safe_row_text(row, column)
        if value == "Not available" and column in {
            "research_score",
            "momentum_score",
            "momentum_1m",
            "momentum_3m",
            "momentum_6m",
            "momentum_12m",
            "volatility_adjusted_momentum",
            "distance_from_52week_high",
            "country_breadth_score",
            "sector_breadth_score",
            "cluster_score",
            "dr_quality_score",
            "average_traded_value_20d",
        }:
            value = _safe_numeric_text(row, column)
        rows.append({"item": label, "value": value, "source": source, "note": ""})
    return rows


def _signal_warning_rows(row: pd.Series) -> list[dict[str, str]]:
    rows = []
    for label, column in [
        ("Failed filters", "failed_filters"),
        ("Data-quality warning", "data_quality_warning"),
        ("DR data-quality warning", "dr_data_quality_warning"),
    ]:
        value = _safe_row_text(row, column, fallback="")
        if value:
            rows.append({"item": label, "value": value, "source": "stock_ranking", "note": "Review before using this research signal."})
    security_type = _safe_row_text(row, "SecurityType", fallback="")
    if security_type.upper() in {"DR", "DRX"}:
        rows.append(
            {
                "item": "DR/DRx separation",
                "value": "DR/DRx proxy",
                "source": "stock_ranking",
                "note": "Do not use DR/DRx rows to judge Thailand domestic breadth.",
            }
        )
    return rows


def _signal_data_quality_rows(row: pd.Series) -> list[dict[str, str]]:
    rows = []
    for label, column in [
        ("Country metadata", "Country"),
        ("Sector metadata", "Sector"),
        ("Industry metadata", "Industry"),
        ("Reason text", "reason"),
        ("Signal type", "signal_type"),
    ]:
        value = _safe_row_text(row, column)
        status = "available" if value != "Not available" else "Needs data source"
        rows.append({"item": label, "value": status, "source": "stock_ranking", "note": value})
    return rows


def _supporting_row_table(row: pd.Series) -> pd.DataFrame:
    items = []
    for column, value in row.items():
        if isinstance(value, dict):
            continue
        try:
            missing = bool(pd.isna(value))
        except (TypeError, ValueError):
            missing = False
        items.append({"column": str(column), "value": "Not available" if missing else str(value)})
    return pd.DataFrame(items)


def _show_startup_checklist(rows: list[StartupChecklistRow]) -> None:
    st.subheader("Yahoo Startup Checklist")
    if not rows:
        st.info("No startup checklist rows available.")
        return
    table = pd.DataFrame([row.__dict__ for row in rows])
    blocker_count = int(table["status"].eq("blocker").sum())
    warning_count = int(table["status"].eq("warning").sum())
    if blocker_count:
        st.error(f"{blocker_count} startup blocker(s) found. Details are available below.")
    elif warning_count:
        st.warning(f"{warning_count} startup warning(s) found. Details are available below.")
    else:
        st.success("No startup blockers detected.")
    with st.expander("Startup checklist details", expanded=bool(blocker_count)):
        render_dataframe(st, table)
        for row in rows:
            message = f"{row.item}: {row.detail}"
            if row.next_step:
                message = f"{message} Next step: {row.next_step}"
            if row.status == "blocker":
                st.error(message)
            elif row.status == "warning":
                st.warning(message)


def _show_yahoo_startup_state(rows: list[StartupChecklistRow], demo_reference_enabled: bool) -> None:
    summary = summarize_yahoo_startup_state(rows, demo_reference_enabled=demo_reference_enabled)
    message = f"{summary.headline}. {summary.detail}"
    if summary.status == "blocked":
        st.error(message)
    elif summary.status == "demo_ready":
        st.success(message)
    elif summary.status == "production_warning":
        st.warning(message)
    else:
        st.success(message)


def _show_yahoo_smoke_test_control(pipeline_config: dict, startup_rows: list[StartupChecklistRow]) -> None:
    st.subheader("Yahoo Historical Smoke Test")
    st.info("Historical Yahoo OHLCV smoke test only. Not realtime, not data completeness validation, and not investment advice.")
    hard_blockers = {"Configured Yahoo tickers", "yfinance availability", "Yahoo adapter config", "Yahoo data loading", "Yahoo cache directory"}
    smoke_blockers = [row for row in startup_rows if row.status == "blocker" and row.item in hard_blockers]
    if smoke_blockers:
        for row in smoke_blockers:
            st.warning(f"Smoke test blocked: {row.item}. {row.next_step or row.detail}")
        return
    if st.button("Run Yahoo historical smoke test"):
        result = _run_yahoo_smoke_test_once(pipeline_config, _smoke_test_cache_token(pipeline_config))
        _show_yahoo_smoke_test_result(result)


def _show_yahoo_smoke_test_result(result: YahooSmokeTestResult) -> None:
    table = pd.DataFrame(
        [
            {
                "tickers_tested": ", ".join(result.attempted_tickers),
                "rows_loaded": result.rows_loaded,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "cache_path": result.cache_path,
                "cache_exists_before": result.cache_exists_before,
                "cache_exists_after": result.cache_exists_after,
                "cache_status": result.cache_status,
                "error": result.error,
            }
        ]
    )
    _show_table("Yahoo Smoke Test Result", table)
    for warning in result.warnings:
        st.warning(warning)
    summary = summarize_yahoo_smoke_test_state(result)
    if result.error:
        st.error(f"{summary.headline}. {summary.detail}")
    elif result.rows_loaded > 0:
        st.success("Yahoo historical smoke test loaded cached or historical OHLCV rows.")


def _show_production_reference_readiness(rows: list[ProductionReferenceReadinessRow], demo_reference_enabled: bool = False) -> None:
    st.subheader("Production Reference Readiness")
    if not rows:
        st.info("No production reference readiness rows available.")
        return
    table = pd.DataFrame([row.__dict__ for row in rows])
    missing_count = sum(row.status == "missing" for row in rows)
    invalid_count = sum(row.status == "invalid" for row in rows)
    sample_count = sum(row.status == "sample" for row in rows)
    if demo_reference_enabled and (missing_count or invalid_count):
        st.warning(
            f"{missing_count + invalid_count} production reference issue(s) found. "
            "Demo mode is being used for smoke testing."
        )
    elif missing_count or invalid_count:
        st.warning(f"{missing_count + invalid_count} production reference issue(s) found.")
    elif sample_count:
        st.warning(f"{sample_count} fake/sample production reference file(s) configured.")
    else:
        st.success("Configured production reference files have required readiness checks.")
    with st.expander("Production readiness warnings", expanded=False):
        render_dataframe(st, table)
        for row in rows:
            if row.status in {"missing", "invalid"}:
                st.warning(f"{row.reference}: {row.detail} {row.next_step}".strip())
            elif row.status == "sample":
                st.warning(f"{row.reference}: fake/sample reference detected. {row.next_step}".strip())


def build_backtest_dashboard_tables(outputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Build report-ready dashboard tables for backtest outputs."""
    tables = {
        "Backtest Assumption Summary": outputs.get("backtest_summary", pd.DataFrame()),
        "Backtest Portfolio Path": outputs.get("backtest_portfolio", pd.DataFrame()),
        "Backtest Positions": outputs.get("backtest_positions", pd.DataFrame()),
        "Backtest Instrument Metrics": outputs.get("backtest_instrument_metrics", pd.DataFrame()),
        "Backtest Warnings": outputs.get("backtest_warnings", pd.DataFrame()),
    }
    return {name: table for name, table in tables.items() if isinstance(table, pd.DataFrame) and not table.empty}


def _show_backtest_page(outputs: dict[str, pd.DataFrame]) -> None:
    st.info("Backtest outputs are research assumptions only. They are not financial advice, trading advice, or future-return guarantees.")
    tables = build_backtest_dashboard_tables(outputs)
    if not tables:
        st.warning("No backtest data available. Enable research backtest assumptions and provide aligned price/signal data.")
        return
    for title, table in tables.items():
        _show_table(title, table)


def _sidebar_backtest_config(enabled: bool) -> BacktestConfig | None:
    if not enabled:
        return None
    return BacktestConfig(
        max_gross_exposure=st.sidebar.slider("Max gross exposure", min_value=0.0, max_value=1.0, value=1.0, step=0.05),
        max_position_weight=st.sidebar.slider("Max position weight", min_value=0.01, max_value=1.0, value=0.25, step=0.01),
        signal_threshold=st.sidebar.number_input("Signal threshold", min_value=0.0, value=0.0, step=1.0),
        rebalance_lag=st.sidebar.number_input("Rebalance lag", min_value=0, value=1, step=1),
    )


def _show_status_tables(outputs: dict[str, pd.DataFrame]) -> None:
    st.subheader("Data Source Status")
    st.caption("Detailed source, reference, and optional-layer diagnostics are grouped below.")
    with st.expander("Data source and reference diagnostics", expanded=False):
        _show_table("Reference Data Status", outputs.get("data_quality_report"))
        _show_table("Thailand Reference Status", outputs.get("thailand_reference_report"))
        _show_table("Thailand Eligibility Status", outputs.get("thailand_eligibility_report"))
        _show_table("Thailand DR / DRx Status", outputs.get("thailand_dr_mapping_report"))
        _show_table("DR Execution Data Quality", outputs.get("dr_execution_quality_data_report"))
        _show_table("DR Fair Value Coverage", outputs.get("dr_fair_value_coverage_report"))
        _show_table("DR Tracking Coverage", outputs.get("dr_tracking_coverage_report"))
        _show_table("Tickers Missing Metadata", outputs.get("reference_data_report"))
        _show_table("Pipeline Layer Status", outputs.get("pipeline_layer_status"))
    warnings = outputs.get("warnings")
    if warnings is not None and not warnings.empty:
        _show_pipeline_warnings(warnings["warning"].dropna().astype(str).tolist())


def build_demo_run_summary(
    outputs: dict[str, pd.DataFrame],
    demo_reference_enabled: bool,
    production_readiness_rows: list[ProductionReferenceReadinessRow] | None = None,
) -> pd.DataFrame:
    """Return a compact first-run summary without changing pipeline outputs."""
    production_rows = production_readiness_rows or []
    production_issue_count = sum(row.status in {"missing", "invalid"} for row in production_rows)
    data_quality = outputs.get("data_quality_report", pd.DataFrame())
    metadata_coverage = ""
    if isinstance(data_quality, pd.DataFrame) and not data_quality.empty and "metadata_coverage_pct" in data_quality.columns:
        metadata_coverage = f"{float(data_quality['metadata_coverage_pct'].iloc[0]):.1f}%"
    return pd.DataFrame(
        [
            {
                "yahoo_data_status": "Loaded historical/cache OHLCV" if not outputs.get("global_flow_summary", pd.DataFrame()).empty else "No flow rows loaded",
                "demo_reference_status": "Enabled; fake/sample-only" if demo_reference_enabled else "Disabled; production references configured",
                "global_flow_rows": _row_count(outputs.get("global_flow_summary")),
                "asset_class_flow_rows": _row_count(outputs.get("asset_class_flow_summary")),
                "metadata_coverage": metadata_coverage,
                "production_readiness_status": (
                    f"{production_issue_count} production reference issue(s); not production-ready"
                    if production_issue_count
                    else "No missing/invalid production reference files detected"
                ),
            }
        ]
    )


def _show_demo_run_summary(
    outputs: dict[str, pd.DataFrame],
    demo_reference_enabled: bool,
    production_readiness_rows: list[ProductionReferenceReadinessRow],
) -> None:
    st.subheader("Demo Run Summary")
    if demo_reference_enabled:
        st.success("Demo mode is enabled for smoke testing. Not production-ready.")
    else:
        st.info("Production reference mode is selected. Missing local references may limit outputs.")
    render_dataframe(st, build_demo_run_summary(outputs, demo_reference_enabled, production_readiness_rows))
    st.caption("Browser print/PDF mirrors the interactive dashboard. Use the Daily Report page and existing CSV/HTML export helpers for report outputs.")


def summarize_dashboard_warnings(warnings: list[str]) -> dict[str, list[str]]:
    """Group repeated pipeline warnings for a less noisy first-run dashboard."""
    grouped: dict[str, list[str]] = {
        "Hard blockers": [],
        "Production readiness warnings": [],
        "Demo/sample warnings": [],
        "Optional skipped layers": [],
        "Other warnings": [],
    }
    adjusted_close_tickers: list[str] = []
    for warning in warnings:
        lowered = warning.lower()
        if "missing adjusted close for " in lowered:
            ticker = warning.split("missing adjusted close for ", 1)[1].split(";", 1)[0].strip()
            adjusted_close_tickers.append(ticker)
        elif "failed and no usable cache" in lowered or "blocked:" in lowered:
            grouped["Hard blockers"].append(warning)
        elif "fake/sample" in lowered or "demo reference" in lowered:
            grouped["Demo/sample warnings"].append(warning)
        elif "metadata" in lowered or "production" in lowered or "reference" in lowered:
            grouped["Production readiness warnings"].append(warning)
        elif "skipped" in lowered or "missing" in lowered or "limited" in lowered:
            grouped["Optional skipped layers"].append(warning)
        else:
            grouped["Other warnings"].append(warning)
    if adjusted_close_tickers:
        preview = ", ".join(adjusted_close_tickers[:8])
        suffix = "..." if len(adjusted_close_tickers) > 8 else ""
        grouped["Optional skipped layers"].append(
            f"{len(adjusted_close_tickers)} ticker(s) missing adjusted close; using Close as Adjusted Close: {preview}{suffix}"
        )
    return {label: values for label, values in grouped.items() if values}


def _show_pipeline_warnings(warnings: list[str]) -> None:
    grouped = summarize_dashboard_warnings(warnings)
    if not grouped:
        return
    total = sum(len(values) for values in grouped.values())
    st.warning(f"{total} pipeline warning(s) reported. Details are grouped below.")
    for label, values in grouped.items():
        with st.expander(label, expanded=label == "Hard blockers"):
            for warning in values:
                st.warning(warning)


def _show_config_validation_warnings(warnings: list[str]) -> None:
    if not warnings:
        return
    production_warnings = [warning for warning in warnings if "reference path" in warning or "reference" in warning]
    other_warnings = [warning for warning in warnings if warning not in production_warnings]
    if production_warnings:
        st.warning(f"{len(production_warnings)} production reference warning(s). Details are grouped below.")
        with st.expander("Production readiness warnings", expanded=False):
            for warning in production_warnings:
                st.warning(warning)
    for warning in other_warnings:
        st.warning(warning)


def _row_count(table: pd.DataFrame | None) -> int:
    return int(len(table)) if isinstance(table, pd.DataFrame) else 0


def _load_dashboard_config() -> dict | None:
    try:
        return load_yaml(Path("config") / "data_sources.yaml")
    except Exception:
        return None


def _apply_local_thailand_yahoo_universe(config: dict, universe: str) -> dict:
    yahoo_settings = config.get("source_settings", {}).get("yahoo", {})
    reference_data = yahoo_settings.get("reference_data") or {}
    thailand_universe_path = reference_data.get("thailand_universe_path")
    if not thailand_universe_path:
        st.sidebar.warning("Thailand universe path missing; using configured Yahoo tickers.")
        return config
    try:
        thailand_metadata = load_thailand_universe(thailand_universe_path)
        liquidity_path = reference_data.get("thailand_liquidity_path")
        liquidity = load_thailand_liquidity(liquidity_path) if liquidity_path else None
        selection = build_thailand_domestic_yahoo_ticker_universe(
            thailand_metadata_df=thailand_metadata,
            liquidity_df=liquidity,
            universe=universe,
        )
    except Exception as exc:
        st.sidebar.warning(f"Could not build local Thailand Yahoo universe: {exc}")
        return config
    for warning in selection.warnings:
        st.sidebar.warning(warning)
    if not selection.yahoo_tickers:
        st.sidebar.warning("No local Yahoo tickers generated; using configured Yahoo tickers.")
        return config
    st.sidebar.success(f"Using {len(selection.yahoo_tickers)} locally configured Yahoo tickers from {universe}.")
    return apply_yahoo_ticker_universe(config, selection.yahoo_tickers)


@st.cache_data(show_spinner=False)
def _load_prices_once(config: dict, refresh_requested: bool = False, cache_token: str = "") -> tuple[pd.DataFrame, list[str]]:
    adapter = get_data_adapter(config)
    prices = adapter.load_prices()
    return prices, list(getattr(adapter, "warnings", []))


@st.cache_data(show_spinner=False)
def _run_config_pipeline_once(
    config: dict,
    backtest_enabled: bool,
    backtest_config: BacktestConfig | None,
    refresh_requested: bool = False,
    cache_token: str = "",
) -> dict[str, pd.DataFrame]:
    return run_pipeline_from_config(config_path=config, adapter=get_data_adapter(config), backtest_enabled=backtest_enabled, backtest_config=backtest_config)


def _safe_adapter_load(loader, label: str) -> pd.DataFrame | None:
    try:
        return loader()
    except FileNotFoundError:
        st.warning(f"Configured {label} is missing. Related layers will be limited.")
        return None
    except ValueError as exc:
        st.warning(f"Configured {label} has invalid schema and will be skipped. Related {label} layers will be limited.")
        st.caption(str(exc))
        return None
    except NotImplementedError as exc:
        st.warning(str(exc))
        return None


def _smoke_test_cache_token(config: dict) -> str:
    try:
        return yahoo_cache_token(get_data_adapter(config))
    except Exception:
        return ""


@st.cache_data(show_spinner=False)
def _run_yahoo_smoke_test_once(config: dict, cache_token: str = "") -> YahooSmokeTestResult:
    return run_yahoo_historical_smoke_test(get_data_adapter(config))


if __name__ == "__main__":
    main()
