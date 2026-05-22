from __future__ import annotations

from pathlib import Path

import pandas as pd


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
    }


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
