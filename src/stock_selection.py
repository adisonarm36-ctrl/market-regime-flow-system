from __future__ import annotations

import pandas as pd


def build_research_candidates(
    metadata_df: pd.DataFrame,
    momentum_df: pd.DataFrame,
    country_regime_df: pd.DataFrame | None = None,
    sector_breadth_df: pd.DataFrame | None = None,
    cluster_summary_df: pd.DataFrame | None = None,
    redundancy_report_df: pd.DataFrame | None = None,
    dr_quality_df: pd.DataFrame | None = None,
    min_liquidity: float = 0,
) -> pd.DataFrame:
    """Build ranked research candidates with reasons, failed filters, and data warnings."""
    if "Ticker" not in metadata_df.columns or "Ticker" not in momentum_df.columns:
        raise ValueError("metadata_df and momentum_df must include Ticker")

    result = metadata_df.merge(momentum_df, on="Ticker", how="left")
    result = _merge_country_regime(result, country_regime_df)
    result = _merge_sector_breadth(result, sector_breadth_df)
    result = _merge_cluster_summary(result, cluster_summary_df)
    result = _merge_dr_quality(result, dr_quality_df)

    redundant = set()
    if redundancy_report_df is not None and not redundancy_report_df.empty and "redundant_ticker" in redundancy_report_df.columns:
        redundant = set(redundancy_report_df["redundant_ticker"].dropna())

    result["failed_filters"] = result.apply(lambda row: _failed_filters(row, redundant, min_liquidity), axis=1)
    result["data_quality_warning"] = result.apply(_data_quality_warning, axis=1)
    result["research_score"] = _research_score(result)
    result["reason"] = result.apply(_reason_text, axis=1)
    result["signal_type"] = "research signal only"

    return result.sort_values("research_score", ascending=False).reset_index(drop=True)


def _merge_country_regime(result: pd.DataFrame, country_regime_df: pd.DataFrame | None) -> pd.DataFrame:
    if country_regime_df is None or country_regime_df.empty or "Country" not in result.columns:
        result["country_breadth_score"] = pd.NA
        result["country_regime"] = pd.NA
        return result
    country = country_regime_df.rename(columns={"country": "Country", "breadth_score": "country_breadth_score", "regime": "country_regime"})
    return result.merge(country[["Country", "country_breadth_score", "country_regime"]].drop_duplicates("Country"), on="Country", how="left")


def _merge_sector_breadth(result: pd.DataFrame, sector_breadth_df: pd.DataFrame | None) -> pd.DataFrame:
    if sector_breadth_df is None or sector_breadth_df.empty or "Sector" not in result.columns or "Sector" not in sector_breadth_df.columns:
        result["sector_breadth_score"] = pd.NA
        return result
    sector = sector_breadth_df.rename(columns={"breadth_score": "sector_breadth_score"})
    return result.merge(sector[["Sector", "sector_breadth_score"]].drop_duplicates("Sector"), on="Sector", how="left")


def _merge_cluster_summary(result: pd.DataFrame, cluster_summary_df: pd.DataFrame | None) -> pd.DataFrame:
    if cluster_summary_df is None or cluster_summary_df.empty:
        result["cluster_score"] = pd.NA
        return result
    if "Ticker" in cluster_summary_df.columns:
        return result.merge(cluster_summary_df[["Ticker", "cluster", "cluster_score"]], on="Ticker", how="left")
    if "cluster" in result.columns and "cluster" in cluster_summary_df.columns:
        return result.merge(cluster_summary_df[["cluster", "cluster_score"]].drop_duplicates("cluster"), on="cluster", how="left")
    result["cluster_score"] = pd.NA
    return result


def _merge_dr_quality(result: pd.DataFrame, dr_quality_df: pd.DataFrame | None) -> pd.DataFrame:
    result["dr_quality_score"] = pd.NA
    if dr_quality_df is None or dr_quality_df.empty:
        return result
    dr = dr_quality_df.rename(columns={"DR_Ticker": "Ticker", "data_quality_warning": "dr_data_quality_warning"})
    columns = [column for column in ["Ticker", "dr_quality_score", "data_quality_warning"] if column in dr.columns]
    columns = [column for column in ["Ticker", "dr_quality_score", "dr_data_quality_warning"] if column in dr.columns]
    return result.drop(columns=["dr_quality_score"]).merge(dr[columns].drop_duplicates("Ticker"), on="Ticker", how="left")


def _research_score(result: pd.DataFrame) -> pd.Series:
    components = []
    for column in ["momentum_score", "country_breadth_score", "sector_breadth_score", "cluster_score"]:
        if column in result.columns:
            components.append(pd.to_numeric(result[column], errors="coerce"))
    if "dr_quality_score" in result.columns:
        components.append(pd.to_numeric(result["dr_quality_score"], errors="coerce"))
    if not components:
        return pd.Series(0, index=result.index)
    return pd.concat(components, axis=1).mean(axis=1, skipna=True).fillna(0)


def _failed_filters(row: pd.Series, redundant: set[str], min_liquidity: float) -> str:
    failed = []
    liquidity = row.get("liquidity", row.get("average_traded_value_20d"))
    if pd.notna(liquidity) and liquidity < min_liquidity:
        failed.append("liquidity")
    if row.get("Ticker") in redundant:
        failed.append("redundancy")
    if pd.notna(row.get("above_200ma")) and not bool(row.get("above_200ma")):
        failed.append("below_200ma")
    return ";".join(failed)


def _data_quality_warning(row: pd.Series) -> str:
    warnings = []
    if pd.isna(row.get("momentum_score")):
        warnings.append("missing_momentum")
    if pd.isna(row.get("country_breadth_score")):
        warnings.append("missing_country_breadth")
    if pd.isna(row.get("sector_breadth_score")):
        warnings.append("missing_sector_breadth")
    if row.get("SecurityType") in {"DR", "DRx"} and pd.isna(row.get("dr_quality_score")):
        warnings.append("missing_dr_quality")
    if pd.notna(row.get("dr_data_quality_warning")):
        warnings.append(str(row.get("dr_data_quality_warning")))
    return ";".join([warning for warning in warnings if warning])


def _reason_text(row: pd.Series) -> str:
    parts = []
    for label, column in [
        ("momentum", "momentum_score"),
        ("country breadth", "country_breadth_score"),
        ("sector breadth", "sector_breadth_score"),
        ("cluster", "cluster_score"),
        ("DR execution", "dr_quality_score"),
    ]:
        value = row.get(column)
        if pd.notna(value):
            parts.append(f"{label}={float(value):.2f}")
    return "; ".join(parts) if parts else "No complete signal metrics available"
