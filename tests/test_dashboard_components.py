import pandas as pd

from src.dashboard_components import (
    MetricCard,
    badge_list_markdown,
    badge_markdown,
    build_table_index,
    callout_markdown,
    empty_state_markdown,
    metric_card_markdown,
    normalize_status,
    render_dataframe,
    safe_display_text,
    section_header_markdown,
    status_label,
    summarize_data_quality_status,
    table_shape_text,
)


class FakeStreamlit:
    def __init__(self) -> None:
        self.dataframe_calls = []

    def dataframe(self, table, **kwargs) -> None:
        self.dataframe_calls.append((table, kwargs))


def test_status_badges_are_textual_and_stable():
    assert normalize_status("warning") == "warning"
    assert normalize_status("unknown-status") == "info"
    assert status_label("blocker") == "Blocker"
    assert badge_markdown("Low Data Confidence", "warning") == "`[Warning] Low Data Confidence`"
    assert badge_list_markdown([("Backtest Supported", "ok"), "Watchlist"]) == "`[OK] Backtest Supported` `[Info] Watchlist`"


def test_section_header_and_metric_card_markdown_include_context():
    header = section_header_markdown("Data Quality", subtitle="Reference coverage", status="warning")
    card = metric_card_markdown(
        MetricCard(
            title="Momentum Score",
            value="82.50",
            status="ok",
            detail="Research signal only.",
            caption="Calculated upstream.",
        )
    )

    assert "### Data Quality" in header
    assert "`[Warning] Warning`" in header
    assert "Reference coverage" in header
    assert "**Momentum Score**" in card
    assert "`82.50`" in card
    assert "Research signal only." in card


def test_callout_and_empty_state_markdown_are_explicit():
    callout = callout_markdown("Missing metadata.", level="warning", title="Data Quality")
    empty = empty_state_markdown("Needs price data.", action="Upload CSV or use configured source.")

    assert "**Data Quality**" in callout
    assert "Missing metadata." in callout
    assert "**No data available.**" in empty
    assert "Next step: Upload CSV or use configured source." in empty


def test_data_quality_summary_reports_counts_and_worst_status():
    rows = [
        {"layer": "metadata", "status": "ok"},
        {"layer": "DR mapping", "status": "warning"},
        {"layer": "Yahoo", "status": "blocker"},
    ]

    summary = summarize_data_quality_status(rows)

    assert summary.total == 3
    assert summary.counts == {"ok": 1, "warning": 1, "blocker": 1}
    assert summary.worst_status == "blocker"
    assert "worst status: Blocker" in summary.headline


def test_data_quality_summary_accepts_dataframe():
    table = pd.DataFrame({"status": ["ready", "sample", "missing"]})

    summary = summarize_data_quality_status(table)

    assert summary.total == 3
    assert summary.worst_status == "missing"
    assert summary.counts["sample"] == 1


def test_render_dataframe_uses_current_streamlit_width_api():
    fake_st = FakeStreamlit()
    table = pd.DataFrame({"Ticker": ["DEMO"], "Score": [1.0]})

    render_dataframe(fake_st, table)

    assert fake_st.dataframe_calls == [(table, {"width": "stretch"})]


def test_table_index_summarizes_non_empty_tables_without_rows():
    tables = {
        "available": pd.DataFrame({"Ticker": ["AAA", "BBB"], "Score": [1.0, 2.0]}),
        "empty": pd.DataFrame(),
        "not_a_table": "skip",
    }

    index = build_table_index(tables)

    assert table_shape_text(tables["available"]) == "2 row(s), 2 column(s)"
    assert index.to_dict("records") == [
        {"table": "available", "rows": 2, "columns": 2, "status": "available"}
    ]


def test_safe_display_text_does_not_invent_missing_values():
    assert safe_display_text(None) == "Not available"
    assert safe_display_text(float("nan")) == "Not available"
    assert safe_display_text("") == "Not available"
    assert safe_display_text(" AAA ") == "AAA"

