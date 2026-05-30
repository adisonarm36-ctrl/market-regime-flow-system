from __future__ import annotations

from pathlib import Path

import pandas as pd


REPORT_SECTION_FIELDS = ("Fact", "Assumption", "Recommendation", "Warning")


def generate_daily_flow_summary(global_flow_summary: pd.DataFrame, limit: int = 5) -> str:
    """Generate a metric-backed global flow proxy narrative."""
    if global_flow_summary.empty:
        return "Global flow signal skipped: no flow metrics available."
    top = global_flow_summary.sort_values("flow_score", ascending=False).head(limit)
    items = [f"{row.Ticker}: flow_score={row.flow_score:.2f}, classification={row.flow_classification}" for row in top.itertuples()]
    return "Research signal - global flow proxy leaders: " + "; ".join(items)


def generate_country_regime_summary(country_breadth_summary: pd.DataFrame) -> str:
    """Generate a metric-backed country regime narrative."""
    if country_breadth_summary.empty:
        return "Country regime skipped: no country breadth metrics available."
    rows = []
    for row in country_breadth_summary.dropna(subset=["breadth_score"], how="any").itertuples():
        rows.append(f"{row.country}: breadth_score={row.breadth_score:.2f}, regime={row.regime}")
    return "Research signal - country regimes: " + "; ".join(rows) if rows else "Country regime skipped: breadth_score missing."


def generate_thailand_market_summary(thailand_market_health: pd.DataFrame) -> str:
    """Generate a metric-backed Thailand market health narrative."""
    if thailand_market_health.empty:
        return "Thailand market health skipped: no eligible Thailand data available."
    row = thailand_market_health.iloc[0]
    if "missing_data" in row and pd.notna(row["missing_data"]):
        return f"Thailand market health skipped: {row['missing_data']}."
    return (
        f"Research signal - Thailand {row.get('universe', 'domestic universe')}: "
        f"breadth_score={float(row['breadth_score']):.2f}, regime={row['regime']}, "
        f"pct_above_50ma={float(row['pct_above_50ma']):.2f}, pct_above_200ma={float(row['pct_above_200ma']):.2f}"
    )


def generate_sector_summary(sector_breadth_summary: pd.DataFrame, limit: int = 5) -> str:
    """Generate a metric-backed sector breadth narrative."""
    if sector_breadth_summary.empty:
        return "Sector breadth skipped: no sector metrics available."
    rows = []
    for row in sector_breadth_summary.dropna(subset=["breadth_score"]).head(limit).itertuples():
        rows.append(f"{row.Sector}: breadth_score={row.breadth_score:.2f}, regime={row.regime}")
    return "Research signal - strongest sectors by breadth: " + "; ".join(rows) if rows else "Sector breadth skipped: breadth_score missing."


def generate_cluster_summary(cluster_summary: pd.DataFrame, limit: int = 5) -> str:
    """Generate a metric-backed cluster narrative."""
    if cluster_summary.empty:
        return "Cluster analysis skipped: no correlation cluster metrics available."
    rows = []
    for row in cluster_summary.head(limit).itertuples():
        rows.append(f"cluster={row.cluster}: cluster_score={row.cluster_score:.2f}, cluster_momentum={row.cluster_momentum:.4f}")
    return "Research signal - top correlation clusters: " + "; ".join(rows)


def generate_stock_selection_summary(stock_ranking: pd.DataFrame, limit: int = 5) -> str:
    """Generate a metric-backed research candidate narrative without buy/sell language."""
    if stock_ranking.empty:
        return "Stock ranking skipped: no research candidates available."
    rows = []
    for row in stock_ranking.head(limit).itertuples():
        rows.append(f"{row.Ticker}: research_score={row.research_score:.2f}, failed_filters={row.failed_filters or 'none'}")
    return "Research signal - candidates: " + "; ".join(rows)


def generate_dr_quality_summary(dr_quality_ranking: pd.DataFrame, limit: int = 5) -> str:
    """Generate a metric-backed DR execution quality narrative."""
    if dr_quality_ranking.empty:
        return "DR quality skipped: no DR mapping or execution data available."
    if "DR_Ticker" not in dr_quality_ranking.columns:
        warning = dr_quality_ranking.get("data_quality_warning", pd.Series(["missing DR execution data"])).iloc[0]
        return f"DR quality skipped: {warning}."
    rows = []
    for row in dr_quality_ranking.head(limit).itertuples():
        rows.append(f"{row.DR_Ticker}: underlying={row.Underlying_Ticker}, dr_quality_score={row.dr_quality_score:.2f}, execution_rank={row.execution_rank:.0f}")
    return "Research signal - DR execution quality: " + "; ".join(rows)


def generate_backtest_summary(backtest_summary: pd.DataFrame) -> str:
    """Generate a research-assumption backtest narrative with metric values."""
    if backtest_summary.empty:
        return "Backtest skipped: no research backtest assumptions or metrics available."
    row = backtest_summary.iloc[0]
    if int(row.get("observations", 0) or 0) == 0:
        return "Backtest skipped: no aligned return observations available."
    return (
        "Research signal - backtest assumptions: "
        f"total_return={float(row['total_return']):.4f}, "
        f"annualized_volatility={float(row['annualized_volatility']):.4f}, "
        f"max_drawdown={float(row['max_drawdown']):.4f}, "
        f"hit_rate={float(row['hit_rate']):.4f}, "
        f"average_gross_exposure={float(row['average_gross_exposure']):.4f}. "
        "This is not financial advice, a recommendation, or a guarantee of future results."
    )


def build_backtest_report_tables(outputs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Return non-empty backtest tables for CSV/HTML report exports."""
    table_names = [
        "backtest_summary",
        "backtest_portfolio",
        "backtest_positions",
        "backtest_instrument_metrics",
        "backtest_warnings",
    ]
    return {
        name: table
        for name in table_names
        if isinstance((table := outputs.get(name)), pd.DataFrame) and not table.empty
    }


def build_daily_report(outputs: dict[str, pd.DataFrame]) -> dict[str, str]:
    """Build all daily report narrative sections from pipeline outputs."""
    return {
        "global_flow": generate_daily_flow_summary(outputs.get("global_flow_summary", pd.DataFrame())),
        "country_regime": generate_country_regime_summary(outputs.get("country_breadth_summary", pd.DataFrame())),
        "thailand_market": generate_thailand_market_summary(outputs.get("thailand_market_health", pd.DataFrame())),
        "sector": generate_sector_summary(outputs.get("sector_breadth_summary", pd.DataFrame())),
        "cluster": generate_cluster_summary(outputs.get("cluster_summary", pd.DataFrame())),
        "stock_selection": generate_stock_selection_summary(outputs.get("stock_ranking", pd.DataFrame())),
        "dr_quality": generate_dr_quality_summary(outputs.get("dr_quality_ranking", pd.DataFrame())),
        "backtest": generate_backtest_summary(outputs.get("backtest_summary", pd.DataFrame())),
    }


def build_narrative_report_sections(outputs: dict[str, pd.DataFrame]) -> dict[str, dict[str, str]]:
    """Build structured report sections from existing outputs without adding metrics."""
    daily_report = build_daily_report(outputs)
    return {
        "Market Summary": {
            "Fact": " ".join(
                [
                    daily_report["global_flow"],
                    daily_report["country_regime"],
                    daily_report["thailand_market"],
                    daily_report["sector"],
                ]
            ),
            "Assumption": "Market summary uses configured historical prices, breadth outputs, and local reference data where available.",
            "Recommendation": "No recommendation is generated. Review these research signals with the supporting metrics and warnings.",
            "Warning": _warning_text(outputs, ["warnings"]),
        },
        "Top Signals": {
            "Fact": daily_report["stock_selection"],
            "Assumption": "Top signals use the existing stock_ranking output and do not change ranking, momentum, or filter calculations.",
            "Recommendation": "Use as a research review list only; no trade instruction is produced.",
            "Warning": _stock_signal_warning_text(outputs.get("stock_ranking", pd.DataFrame())),
        },
        "Key Risks": {
            "Fact": _warning_text(outputs, ["warnings", "backtest_warnings", "dr_quality_warnings"]),
            "Assumption": "Missing optional layers are reported as warnings or skipped instead of being inferred.",
            "Recommendation": "Inspect warning rows and raw output tables before relying on any research signal.",
            "Warning": _data_quality_warning_text(outputs),
        },
        "Backtest Evidence": {
            "Fact": daily_report["backtest"],
            "Assumption": "Backtests are opt-in historical research assumptions using existing backtest outputs only.",
            "Recommendation": "Do not treat backtest metrics as predictive accuracy or future performance guidance.",
            "Warning": _warning_text(outputs, ["backtest_warnings"]),
        },
        "Data Quality Notes": {
            "Fact": _data_quality_fact_text(outputs),
            "Assumption": "Yahoo is historical/cache-based only; metadata, sectors, countries, Thailand universes, and DR mappings come from local references.",
            "Recommendation": "Use verified local reference files for production research and keep demo/sample warnings visible.",
            "Warning": _data_quality_warning_text(outputs),
        },
        "Appendix / Raw Data": {
            "Fact": _raw_table_fact_text(outputs),
            "Assumption": "CSV raw-data export writes each non-empty DataFrame; HTML export contains narrative sections.",
            "Recommendation": "Confirmed export formats are CSV and HTML only. Markdown and PDF remain future enhancements.",
            "Warning": "Raw tables may include fake/demo sample rows when demo reference mode or sample data is used.",
        },
    }


def flatten_narrative_report_sections(sections: dict[str, dict[str, str]]) -> dict[str, str]:
    """Flatten structured report sections for existing narrative HTML export."""
    flattened: dict[str, str] = {}
    for section_name, fields in sections.items():
        key = section_name.lower().replace(" / ", "_").replace(" ", "_")
        parts = []
        for field in REPORT_SECTION_FIELDS:
            value = fields.get(field)
            if value:
                parts.append(f"{field}: {value}")
        flattened[key] = " ".join(parts)
    return flattened


def _warning_text(outputs: dict[str, pd.DataFrame], keys: list[str]) -> str:
    warnings: list[str] = []
    for key in keys:
        table = outputs.get(key, pd.DataFrame())
        if not isinstance(table, pd.DataFrame) or table.empty:
            continue
        column = "warning" if "warning" in table.columns else table.columns[0]
        warnings.extend(str(value).strip() for value in table[column].dropna().head(5) if str(value).strip())
    return "; ".join(warnings) if warnings else "No warning rows reported by current outputs."


def _stock_signal_warning_text(stock_ranking: pd.DataFrame) -> str:
    if not isinstance(stock_ranking, pd.DataFrame) or stock_ranking.empty:
        return "No stock_ranking rows available."
    warning_columns = [column for column in ["failed_filters", "data_quality_warning", "dr_data_quality_warning"] if column in stock_ranking.columns]
    warnings: list[str] = []
    for column in warning_columns:
        warnings.extend(str(value).strip() for value in stock_ranking[column].dropna().head(5) if str(value).strip())
    return "; ".join(warnings) if warnings else "No failed-filter or data-quality warnings reported in the top signal rows."


def _data_quality_fact_text(outputs: dict[str, pd.DataFrame]) -> str:
    quality_keys = [
        "data_quality_report",
        "reference_data_report",
        "thailand_reference_report",
        "pipeline_layer_status",
        "dr_quality_warnings",
    ]
    available = [key for key in quality_keys if isinstance(outputs.get(key), pd.DataFrame) and not outputs[key].empty]
    if not available:
        return "No data-quality report tables are available in current outputs."
    return "Available data-quality tables: " + ", ".join(available)


def _data_quality_warning_text(outputs: dict[str, pd.DataFrame]) -> str:
    warning = _warning_text(outputs, ["warnings", "dr_quality_warnings"])
    if warning != "No warning rows reported by current outputs.":
        return warning
    available_fact = _data_quality_fact_text(outputs)
    if available_fact.startswith("No data-quality"):
        return "Data-quality status is unavailable; missing optional data should be treated as skipped."
    return "Review available data-quality tables for missing metadata, demo/sample references, stale cache, and skipped layers."


def _raw_table_fact_text(outputs: dict[str, pd.DataFrame]) -> str:
    names = [name for name, table in outputs.items() if isinstance(table, pd.DataFrame) and not table.empty]
    if not names:
        return "No non-empty raw output tables are available for export."
    return "Non-empty raw tables available for CSV export: " + ", ".join(names)


def export_report_to_csv(outputs: dict[str, pd.DataFrame], output_dir: str | Path) -> list[Path]:
    """Export every non-empty report table to CSV."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, table in outputs.items():
        if isinstance(table, pd.DataFrame) and not table.empty:
            path = root / f"{name}.csv"
            table.to_csv(path, index=False)
            paths.append(path)
    return paths


def export_report_to_html(report_sections: dict[str, str], path: str | Path) -> Path:
    """Export report narrative sections to a simple HTML file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"<section><h2>{name.replace('_', ' ').title()}</h2><p>{text}</p></section>" for name, text in report_sections.items())
    output_path.write_text(f"<!doctype html><html><body><h1>Daily Market Research Report</h1>{body}</body></html>", encoding="utf-8")
    return output_path
