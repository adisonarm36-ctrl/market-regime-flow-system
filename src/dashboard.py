from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_loader import pivot_prices, pivot_volume
from src.report_generator import build_daily_report
from src.topdown_pipeline import run_topdown_pipeline


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

    with st.sidebar:
        st.header("CSV Inputs")
        ohlcv_upload = st.file_uploader("OHLCV CSV", type=["csv"])
        metadata_upload = st.file_uploader("Metadata CSV", type=["csv"])
        country_upload = st.file_uploader("Country map CSV", type=["csv"])
        asset_upload = st.file_uploader("Asset map CSV", type=["csv"])
        thailand_upload = st.file_uploader("Thailand metadata CSV", type=["csv"])
        dr_mapping_upload = st.file_uploader("DR mapping CSV", type=["csv"])
        dr_ohlcv_upload = st.file_uploader("DR OHLCV CSV", type=["csv"])
        benchmark_ticker = st.text_input("Benchmark ticker", value="")

    ohlcv = _read_csv_upload(ohlcv_upload)
    if ohlcv is None:
        st.info("Upload an OHLCV CSV to run the dashboard. Required columns: Date, Ticker, Open, High, Low, Close, Volume.")
        return

    try:
        price_df = pivot_prices(ohlcv)
        volume_df = pivot_volume(ohlcv)
    except Exception as exc:
        st.error(f"Could not load OHLCV data: {exc}")
        return

    metadata = _read_csv_upload(metadata_upload)
    country_map = _read_csv_upload(country_upload)
    asset_map = _read_csv_upload(asset_upload)
    thailand_metadata = _read_csv_upload(thailand_upload)
    dr_mapping = _read_csv_upload(dr_mapping_upload)
    dr_ohlcv = _read_csv_upload(dr_ohlcv_upload)
    dr_prices = pivot_prices(dr_ohlcv) if dr_ohlcv is not None else None
    dr_volume = pivot_volume(dr_ohlcv) if dr_ohlcv is not None else None

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
        "Sector Breadth",
        "Theme / Correlation Cluster",
        "Stock Ranking",
        "DR Global Proxy",
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
        _show_table("Excluded Securities", outputs.get("excluded_summary"))
    elif page == "Sector Breadth":
        _show_table("Sector Breadth Summary", outputs.get("sector_breadth_summary"))
    elif page == "Theme / Correlation Cluster":
        _show_table("Cluster Summary", outputs.get("cluster_summary"))
        _show_table("Cluster Members", outputs.get("cluster_membership"))
        _show_table("Redundant Instruments", outputs.get("redundancy_report"))
    elif page == "Stock Ranking":
        _show_table("Ranked Research Candidates", outputs.get("stock_ranking"))
    elif page == "DR Global Proxy":
        _show_table("DR Execution Quality", outputs.get("dr_quality_ranking"))
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


if __name__ == "__main__":
    main()
