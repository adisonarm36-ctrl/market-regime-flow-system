from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pandas as pd
import streamlit as st

from src.backtest import BacktestConfig
from src.config_validation import (
    DEMO_REFERENCE_MODE_WARNING,
    apply_demo_reference_mode,
    validate_data_sources_config,
    validate_metadata_schema,
)
from src.config_loader import load_yaml
from src.data_adapters import get_data_adapter
from src.data_adapters.csv_adapter import CsvDataAdapter
from src.data_adapters.yahoo_adapter import YahooDataAdapter
from src.data_loader import pivot_prices, pivot_volume
from src.report_generator import build_daily_report
from src.startup_diagnostics import (
    StartupChecklistRow,
    YahooSmokeTestResult,
    build_yahoo_startup_checklist,
    check_yfinance_available,
    run_yahoo_historical_smoke_test,
    startup_checklist_has_blockers,
    yfinance_missing_guidance,
)
from src.topdown_pipeline import run_pipeline_from_config, run_topdown_pipeline
from src.thailand_reference import load_thailand_liquidity, load_thailand_universe
from src.yahoo_universe import build_thailand_domestic_yahoo_ticker_universe


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"
CONFIG_SOURCE_MODE = "Config source"
MANUAL_FALLBACK_MODE = "Advanced / fallback manual upload"


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
            use_demo_reference_data = st.checkbox(
                "Use bundled fake/demo reference files",
                value=False,
                help="Maps missing local reference paths to bundled fake/sample files for first-run smoke testing only.",
            )
            if use_demo_reference_data:
                st.warning(DEMO_REFERENCE_MODE_WARNING)
                st.caption("Production reference paths remain configured in data_sources.yaml; demo mode only changes this dashboard run.")
        if config is not None:
            for warning in validate_data_sources_config(config):
                st.warning(warning)
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
        for warning in demo_reference_warnings:
            st.warning(warning)
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
            _show_yahoo_smoke_test_control(pipeline_config=disable_yahoo_force_refresh(runtime_config), startup_rows=startup_rows)
            if startup_checklist_has_blockers(startup_rows):
                st.error("Configured Yahoo startup has blockers. Resolve the checklist items or use Advanced / fallback manual upload.")
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
            st.error("Configured Yahoo startup has blockers. Resolve the checklist items or use Advanced / fallback manual upload.")
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

    if page == "Global Flow Map":
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
        _show_table("Ranked Research Candidates", outputs.get("stock_ranking"))
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
        st.warning("No data available for this layer. Missing data is skipped.")
        return
    st.dataframe(table, use_container_width=True)


def _show_startup_checklist(rows: list[StartupChecklistRow]) -> None:
    st.subheader("Yahoo Startup Checklist")
    if not rows:
        st.info("No startup checklist rows available.")
        return
    table = pd.DataFrame([row.__dict__ for row in rows])
    st.dataframe(table, use_container_width=True)
    for row in rows:
        message = f"{row.item}: {row.detail}"
        if row.next_step:
            message = f"{message} Next step: {row.next_step}"
        if row.status == "blocker":
            st.error(message)
        elif row.status == "warning":
            st.warning(message)


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
    if result.error:
        st.error(result.error)
    elif result.rows_loaded > 0:
        st.success("Yahoo historical smoke test loaded cached or historical OHLCV rows.")


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
        for warning in warnings["warning"].dropna():
            st.warning(warning)


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
