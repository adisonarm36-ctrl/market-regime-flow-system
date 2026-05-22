from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.config_validation import validate_metadata_schema
from src.config_loader import load_yaml
from src.data_adapters import get_data_adapter
from src.data_adapters.csv_adapter import CsvDataAdapter
from src.data_adapters.yahoo_adapter import YahooDataAdapter
from src.data_loader import pivot_prices, pivot_volume
from src.report_generator import build_daily_report
from src.topdown_pipeline import run_pipeline_from_config, run_topdown_pipeline


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"


def _read_csv_upload(uploaded_file) -> pd.DataFrame | None:
    if uploaded_file is None:
        return None
    df = pd.read_csv(uploaded_file)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    return df


def main() -> None:
    """Run the Streamlit research dashboard."""
    st.set_page_config(page_title="Market Regime Flow System", layout="wide")
    st.title("Market Regime Flow System")
    st.caption("Research signals only. No financial advice or guaranteed buy/sell recommendations.")
    st.info("Use verified CSV data for research. Bundled sample data is fake/demo data for smoke testing only.")

    with st.sidebar:
        st.header("CSV Inputs")
        data_mode = st.radio("Data mode", ["Manual upload / sample", "Config source"], index=0)
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

    if data_mode == "Config source":
        config = load_yaml(Path("config") / "data_sources.yaml")
        adapter = get_data_adapter(config)
        if isinstance(adapter, YahooDataAdapter):
            st.sidebar.info("Yahoo mode uses delayed/historical yfinance data only. It is not realtime.")
            st.sidebar.write(
                {
                    "tickers": adapter.tickers,
                    "period": adapter.period,
                    "interval": adapter.interval,
                    "cache_dir": str(adapter.cache_dir),
                    "cache_ttl_hours": adapter.cache_ttl_hours,
                }
            )
            cache_path = adapter.cache_path()
            st.sidebar.write(f"Cache path: `{cache_path}`")
            if cache_path.exists():
                st.sidebar.success("Yahoo cache file is available.")
            else:
                st.sidebar.warning("Yahoo cache file is not available yet.")
            if st.sidebar.checkbox("Use cached data if available", value=True):
                adapter.fallback_to_cache = True
        try:
            ohlcv, adapter_warnings = _load_prices_once(config)
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

    if data_mode == "Config source":
        outputs = _run_config_pipeline_once(config)
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


@st.cache_data(show_spinner=False)
def _load_prices_once(config: dict) -> tuple[pd.DataFrame, list[str]]:
    adapter = get_data_adapter(config)
    prices = adapter.load_prices()
    return prices, list(getattr(adapter, "warnings", []))


@st.cache_data(show_spinner=False)
def _run_config_pipeline_once(config: dict) -> dict[str, pd.DataFrame]:
    return run_pipeline_from_config(adapter=get_data_adapter(config))


def _safe_adapter_load(loader, label: str) -> pd.DataFrame | None:
    try:
        return loader()
    except FileNotFoundError:
        st.warning(f"Configured {label} is missing. Related layers will be limited.")
        return None
    except NotImplementedError as exc:
        st.warning(str(exc))
        return None


if __name__ == "__main__":
    main()
