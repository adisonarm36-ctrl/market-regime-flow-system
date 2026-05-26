from __future__ import annotations

import pandas as pd


def build_pipeline_backtest_signals(
    price_df: pd.DataFrame,
    stock_ranking_df: pd.DataFrame,
    dr_mapping_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Build Date x Ticker backtest signals from pipeline stock-ranking outputs."""
    warnings: list[str] = []
    if price_df.empty:
        return pd.DataFrame(), ["backtest skipped: missing price data"]
    if stock_ranking_df.empty:
        return pd.DataFrame(index=price_df.index), ["backtest skipped: missing stock ranking signals"]
    if "Ticker" not in stock_ranking_df.columns or "research_score" not in stock_ranking_df.columns:
        return pd.DataFrame(index=price_df.index), ["backtest skipped: stock ranking missing Ticker or research_score"]

    mapping = _underlying_map(dr_mapping_df)
    signal_scores: dict[str, float] = {}
    for _, row in stock_ranking_df.iterrows():
        ticker = row.get("Ticker")
        if pd.isna(ticker):
            continue
        ticker = str(ticker)
        if _has_failed_filters(row):
            warnings.append(f"backtest signal skipped: {ticker} failed filters")
            continue

        signal_ticker = _signal_ticker(row, ticker, mapping, price_df.columns, warnings)
        if signal_ticker is None:
            continue

        score = pd.to_numeric(row.get("research_score"), errors="coerce")
        if pd.isna(score):
            warnings.append(f"backtest signal skipped: {ticker} missing research_score")
            continue

        signal_scores[signal_ticker] = max(signal_scores.get(signal_ticker, float("-inf")), float(score))

    if not signal_scores:
        return pd.DataFrame(index=price_df.index), warnings + ["backtest skipped: no eligible signals"]

    signal_df = pd.DataFrame(0.0, index=price_df.index, columns=sorted(signal_scores))
    for ticker, score in signal_scores.items():
        signal_df[ticker] = score
    return signal_df, warnings


def backtest_warnings_frame(warnings: list[str]) -> pd.DataFrame:
    """Return warnings as a report-friendly table."""
    return pd.DataFrame({"warning": warnings})


def build_backtest_data_coverage_warnings(
    price_df: pd.DataFrame,
    signal_df: pd.DataFrame,
    price_source_label: str = "historical price data",
) -> list[str]:
    """Return report-ready backtest data coverage warnings and assumptions."""
    warnings = [
        f"backtest source: {price_source_label}; historical research assumptions only, not financial advice",
    ]
    if price_df.empty:
        return warnings + ["backtest coverage warning: missing historical price data"]
    if signal_df.empty:
        return warnings + ["backtest coverage warning: missing backtest signal data"]

    common_dates = price_df.index.intersection(signal_df.index)
    common_tickers = price_df.columns.intersection(signal_df.columns)
    warnings.append(
        "backtest coverage: "
        f"price_dates={len(price_df.index)}, signal_dates={len(signal_df.index)}, "
        f"common_dates={len(common_dates)}, common_tickers={len(common_tickers)}"
    )

    if len(common_dates) == 0:
        warnings.append("backtest coverage warning: no overlapping price and signal dates")
    if len(common_tickers) == 0:
        warnings.append("backtest coverage warning: no overlapping price and signal tickers")

    missing_price_tickers = sorted(set(signal_df.columns) - set(price_df.columns))
    if missing_price_tickers:
        warnings.append(f"backtest coverage warning: signal tickers missing price data: {', '.join(missing_price_tickers)}")

    missing_signal_tickers = sorted(set(price_df.columns) - set(signal_df.columns))
    if missing_signal_tickers:
        warnings.append(f"backtest coverage warning: price tickers without signal data: {', '.join(missing_signal_tickers)}")

    return warnings


def _underlying_map(dr_mapping_df: pd.DataFrame | None) -> dict[str, str]:
    if dr_mapping_df is None or dr_mapping_df.empty:
        return {}
    if not {"DR_Ticker", "UnderlyingTicker"}.issubset(dr_mapping_df.columns):
        return {}
    mapping = dr_mapping_df.dropna(subset=["DR_Ticker", "UnderlyingTicker"])
    return dict(zip(mapping["DR_Ticker"].astype(str), mapping["UnderlyingTicker"].astype(str), strict=False))


def _has_failed_filters(row: pd.Series) -> bool:
    failed = row.get("failed_filters")
    return pd.notna(failed) and str(failed).strip() != ""


def _signal_ticker(
    row: pd.Series,
    ticker: str,
    dr_underlying_map: dict[str, str],
    price_columns: pd.Index,
    warnings: list[str],
) -> str | None:
    security_type = str(row.get("SecurityType", "")).upper()
    is_dr = security_type in {"DR", "DRX"} or ticker in dr_underlying_map
    if is_dr:
        underlying = row.get("UnderlyingTicker")
        if pd.isna(underlying):
            underlying = dr_underlying_map.get(ticker)
        if pd.isna(underlying) or underlying is None:
            warnings.append(f"backtest DR signal skipped: {ticker} missing underlying ticker")
            return None
        underlying = str(underlying)
        if underlying not in price_columns:
            warnings.append(f"backtest DR signal skipped: {ticker} underlying {underlying} missing price data")
            return None
        return underlying

    if ticker not in price_columns:
        warnings.append(f"backtest signal skipped: {ticker} missing price data")
        return None
    return ticker
