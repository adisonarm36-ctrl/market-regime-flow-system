from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_adapters.base import DataAdapter
from src.data_validation import validate_ohlcv
from src.reference_data import load_dr_mapping as load_local_dr_mapping
from src.reference_data import load_metadata as load_local_metadata
from src.reference_data import load_sector_map as load_local_sector_map


SUPPORTED_INTERVALS = {"1d", "5d", "1wk", "1mo", "3mo"}
SUPPORTED_CACHE_FORMATS = {"csv", "parquet"}


class YahooDataAdapter(DataAdapter):
    """Cache-first Yahoo Finance historical data adapter using yfinance."""

    def __init__(
        self,
        tickers: list[str],
        period: str | None = "2y",
        start: str | None = None,
        end: str | None = None,
        interval: str = "1d",
        auto_adjust: bool = True,
        cache_dir: str | Path = "data/cache/yahoo",
        cache_format: str = "parquet",
        cache_ttl_hours: float = 8,
        fallback_to_cache: bool = True,
        force_refresh: bool = False,
        reference_data: dict | None = None,
        yfinance_module: Any | None = None,
    ) -> None:
        self.tickers = [ticker for ticker in tickers if ticker]
        self.period = period
        self.start = start
        self.end = end
        self.interval = interval
        self.auto_adjust = auto_adjust
        self.cache_dir = Path(cache_dir)
        self.cache_format = cache_format
        self.cache_ttl_hours = cache_ttl_hours
        self.fallback_to_cache = fallback_to_cache
        self.force_refresh = force_refresh
        self.reference_data = reference_data or {}
        self._yf = yfinance_module
        self.warnings: list[str] = []
        self.validate_settings()

    @classmethod
    def from_config(cls, settings: dict) -> "YahooDataAdapter":
        """Create a Yahoo adapter from data_sources.yaml yahoo settings."""
        return cls(
            tickers=settings.get("tickers") or [],
            period=settings.get("period", "2y"),
            start=settings.get("start"),
            end=settings.get("end"),
            interval=settings.get("interval", "1d"),
            auto_adjust=settings.get("auto_adjust", True),
            cache_dir=settings.get("cache_dir", "data/cache/yahoo"),
            cache_format=settings.get("cache_format", "parquet"),
            cache_ttl_hours=settings.get("cache_ttl_hours", 8),
            fallback_to_cache=settings.get("fallback_to_cache", True),
            force_refresh=settings.get("force_refresh", False),
            reference_data=settings.get("reference_data") or {},
        )

    def validate_settings(self) -> None:
        """Validate Yahoo adapter settings before any network call."""
        if not self.tickers:
            raise ValueError("YahooDataAdapter requires at least one ticker")
        if self.interval not in SUPPORTED_INTERVALS:
            raise ValueError(f"Unsupported Yahoo interval: {self.interval}. Supported intervals: {', '.join(sorted(SUPPORTED_INTERVALS))}")
        if self.cache_format not in SUPPORTED_CACHE_FORMATS:
            raise ValueError(f"Unsupported cache_format: {self.cache_format}. Use csv or parquet")

    def load_prices(self, force_refresh: bool | None = None) -> pd.DataFrame:
        """Load historical OHLCV data from fresh cache, Yahoo, or stale cache fallback."""
        self.warnings = []
        cache_path = self.cache_path()
        refresh_requested = self.force_refresh if force_refresh is None else bool(force_refresh)
        if not refresh_requested and self._is_cache_fresh(cache_path):
            return self._read_cache(cache_path)

        try:
            downloaded = self._download_from_yahoo()
            normalized = self._normalize_yahoo_output(downloaded)
            self._write_cache(normalized, cache_path)
            return normalized
        except Exception as exc:
            if self.fallback_to_cache and cache_path.exists():
                action = "refresh" if refresh_requested else "fetch"
                self.warnings.append(f"fallback to cache after Yahoo {action} failure: {exc}")
                return self._read_cache(cache_path)
            raise RuntimeError(f"Yahoo historical data fetch failed and no usable cache is available: {exc}") from exc

    def load_metadata(self) -> pd.DataFrame:
        """Load local metadata configured under yahoo.reference_data."""
        return self._load_optional_reference("metadata_path", load_local_metadata, "metadata path missing")

    def load_sector_map(self) -> pd.DataFrame:
        """Load local sector map configured under yahoo.reference_data."""
        return self._load_optional_reference("sector_map_path", load_local_sector_map, "sector map path missing")

    def load_dr_mapping(self) -> pd.DataFrame:
        """Load local DR mapping configured under yahoo.reference_data."""
        return self._load_optional_reference("dr_mapping_path", load_local_dr_mapping, "DR mapping path missing")

    def validate_schema(self) -> list[str]:
        """Validate Yahoo settings and cache output schema when cache exists."""
        warnings: list[str] = []
        try:
            self.validate_settings()
        except ValueError as exc:
            warnings.append(str(exc))
            return warnings

        cache_path = self.cache_path()
        if cache_path.exists():
            result = validate_ohlcv(self._read_cache(cache_path))
            warnings.extend(result.errors)
            warnings.extend(result.warnings)
        for key, label in [
            ("metadata_path", "metadata path missing"),
            ("sector_map_path", "sector map path missing"),
            ("country_map_path", "country map path missing"),
            ("dr_mapping_path", "DR mapping path missing"),
        ]:
            value = self.reference_data.get(key)
            if not value:
                warnings.append(label)
            elif not Path(value).exists():
                warnings.append(f"{label}: {value}")
        return warnings

    def cache_path(self) -> Path:
        """Return deterministic cache path for this query."""
        key = "|".join(
            [
                ",".join(sorted(self.tickers)),
                str(self.period),
                str(self.start),
                str(self.end),
                self.interval,
                str(self.auto_adjust),
            ]
        )
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"yahoo_{digest}.{self.cache_format}"

    def cache_metadata(self, now: datetime | None = None) -> dict[str, Any]:
        """Return cache metadata for dashboard/status displays without loading data."""
        cache_path = self.cache_path()
        metadata: dict[str, Any] = {
            "cache_path": str(cache_path),
            "cache_exists": cache_path.exists(),
            "cache_last_updated": "",
            "cache_age_hours": None,
            "cache_ttl_hours": float(self.cache_ttl_hours),
            "cache_is_fresh": False,
            "cache_is_stale": False,
            "cache_first_enabled": not self.force_refresh,
            "fallback_to_cache": self.fallback_to_cache,
        }
        if not cache_path.exists():
            return metadata

        current_time = now or datetime.now()
        modified = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age_hours = (current_time - modified).total_seconds() / 3600
        is_fresh = age_hours <= float(self.cache_ttl_hours)
        metadata.update(
            {
                "cache_last_updated": modified.strftime("%Y-%m-%d %H:%M:%S"),
                "cache_age_hours": age_hours,
                "cache_is_fresh": is_fresh,
                "cache_is_stale": not is_fresh,
            }
        )
        return metadata

    def _download_from_yahoo(self) -> pd.DataFrame:
        yf = self._yf
        if yf is None:
            import yfinance as yf  # type: ignore

        return yf.download(
            tickers=self.tickers if len(self.tickers) > 1 else self.tickers[0],
            period=self.period if not self.start else None,
            start=self.start,
            end=self.end,
            interval=self.interval,
            auto_adjust=self.auto_adjust,
            group_by="ticker",
            progress=False,
            threads=True,
        )

    def _normalize_yahoo_output(self, raw: pd.DataFrame) -> pd.DataFrame:
        if raw is None or raw.empty:
            self.warnings.append("empty downloaded data")
            raise ValueError("Yahoo returned empty downloaded data")

        frames: list[pd.DataFrame] = []
        if isinstance(raw.columns, pd.MultiIndex):
            level0_values = set(map(str, raw.columns.get_level_values(0)))
            ticker_first = any(ticker in level0_values for ticker in self.tickers)
            for ticker in self.tickers:
                try:
                    ticker_df = raw[ticker] if ticker_first else raw.xs(ticker, axis=1, level=1)
                except KeyError:
                    self.warnings.append(f"Yahoo returned partial data; missing ticker: {ticker}")
                    continue
                frames.append(self._normalize_single_ticker(ticker_df, ticker))
        else:
            if len(self.tickers) != 1:
                self.warnings.append("Yahoo returned single-index columns for multiple tickers; assigning data to first ticker only")
            frames.append(self._normalize_single_ticker(raw, self.tickers[0]))

        if not frames:
            raise ValueError("Yahoo returned no usable ticker data")
        result = pd.concat(frames, ignore_index=True)
        result = result.dropna(subset=["Close"]).sort_values(["Date", "Ticker"]).reset_index(drop=True)
        if result.empty:
            self.warnings.append("all downloaded rows had missing Close")
            raise ValueError("Yahoo data has no rows with Close values")
        present = set(result["Ticker"].unique())
        missing = sorted(set(self.tickers) - present)
        if missing:
            self.warnings.append(f"Yahoo returned partial data; missing tickers: {', '.join(missing)}")
        return result

    def _normalize_single_ticker(self, ticker_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        data = ticker_df.copy()
        data.columns = [str(column) for column in data.columns]
        data = data.reset_index()
        date_column = "Date" if "Date" in data.columns else data.columns[0]
        data = data.rename(columns={date_column: "Date", "Adj Close": "Adjusted Close"})

        required_price_columns = ["Open", "High", "Low", "Close", "Volume"]
        for column in required_price_columns:
            if column not in data.columns:
                data[column] = pd.NA
        if "Adjusted Close" not in data.columns:
            data["Adjusted Close"] = data["Close"]
            if self.auto_adjust:
                self.warnings.append(f"missing adjusted close for {ticker}; using Close as Adjusted Close")

        data["Ticker"] = ticker
        data["Date"] = pd.to_datetime(data["Date"]).dt.tz_localize(None)
        return data[["Date", "Ticker", "Open", "High", "Low", "Close", "Volume", "Adjusted Close"]]

    def _is_cache_fresh(self, cache_path: Path) -> bool:
        if not cache_path.exists():
            return False
        modified = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - modified <= timedelta(hours=float(self.cache_ttl_hours))

    def _read_cache(self, cache_path: Path) -> pd.DataFrame:
        if self.cache_format == "csv":
            df = pd.read_csv(cache_path)
        else:
            df = pd.read_parquet(cache_path)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
        return df.sort_values(["Date", "Ticker"]).reset_index(drop=True)

    def _write_cache(self, df: pd.DataFrame, cache_path: Path) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if self.cache_format == "csv":
            df.to_csv(cache_path, index=False)
        else:
            df.to_parquet(cache_path, index=False)

    def _load_optional_reference(self, key: str, loader, missing_message: str) -> pd.DataFrame:
        path = self.reference_data.get(key)
        if not path:
            self.warnings.append(missing_message)
            return pd.DataFrame()
        try:
            return loader(path)
        except FileNotFoundError:
            self.warnings.append(f"{missing_message}: {path}")
            return pd.DataFrame()
        except ValueError as exc:
            self.warnings.append(
                f"optional reference {key} has invalid schema and will be skipped: {path}. "
                f"{exc}. Related layers will be limited."
            )
            return pd.DataFrame()
