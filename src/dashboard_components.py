from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Iterable, Mapping, Sequence

import pandas as pd


STATUS_ORDER = {
    "ok": 0,
    "ready": 0,
    "available": 0,
    "success": 0,
    "info": 1,
    "sample": 2,
    "warning": 2,
    "limited": 2,
    "missing": 3,
    "invalid": 3,
    "blocker": 4,
    "error": 4,
    "skipped": 4,
}
STATUS_LABELS = {
    "ok": "OK",
    "ready": "Ready",
    "available": "Available",
    "success": "Success",
    "info": "Info",
    "sample": "Sample",
    "warning": "Warning",
    "limited": "Limited",
    "missing": "Missing",
    "invalid": "Invalid",
    "blocker": "Blocker",
    "error": "Error",
    "skipped": "Skipped",
}
CALLOUT_LEVELS = {"info", "success", "warning", "error"}


@dataclass(frozen=True)
class MetricCard:
    """A compact dashboard metric/status card model."""

    title: str
    value: str
    status: str = "info"
    detail: str = ""
    caption: str = ""


@dataclass(frozen=True)
class DataQualitySummary:
    """Aggregated status counts for data-quality/dashboard rows."""

    total: int
    counts: dict[str, int]
    worst_status: str
    headline: str


def normalize_status(status: str | None) -> str:
    """Return a stable status key for dashboard presentation helpers."""
    key = str(status or "info").strip().lower().replace(" ", "_")
    return key if key in STATUS_ORDER else "info"


def status_label(status: str | None) -> str:
    """Return a human-readable status label."""
    key = normalize_status(status)
    return STATUS_LABELS.get(key, key.replace("_", " ").title())


def badge_text(label: str, status: str = "info") -> str:
    """Return a compact text badge that does not rely on color alone."""
    return f"[{status_label(status)}] {str(label).strip()}"


def badge_markdown(label: str, status: str = "info") -> str:
    """Return badge text suitable for Streamlit markdown."""
    return f"`{badge_text(label, status)}`"


def badge_list_markdown(badges: Iterable[tuple[str, str] | str]) -> str:
    """Return a space-separated list of status badges."""
    rendered = []
    for badge in badges:
        if isinstance(badge, tuple):
            label, status = badge
        else:
            label, status = str(badge), "info"
        rendered.append(badge_markdown(label, status))
    return " ".join(rendered)


def section_header_markdown(title: str, subtitle: str = "", status: str | None = None) -> str:
    """Return a consistent markdown section header."""
    parts = [f"### {str(title).strip()}"]
    if status:
        parts.append(badge_markdown(status_label(status), status))
    if subtitle:
        parts.append(str(subtitle).strip())
    return "\n\n".join(parts)


def metric_card_markdown(card: MetricCard) -> str:
    """Return markdown for a compact metric/status card."""
    lines = [
        f"**{card.title}**",
        f"{badge_markdown(card.status, card.status)}",
        f"`{card.value}`",
    ]
    if card.detail:
        lines.append(card.detail)
    if card.caption:
        lines.append(f"_{card.caption}_")
    return "\n\n".join(lines)


def callout_markdown(message: str, level: str = "info", title: str = "") -> str:
    """Return a callout body with a stable status label."""
    normalized = normalize_status(level)
    if normalized not in CALLOUT_LEVELS:
        normalized = "info"
    heading = f"**{title or status_label(normalized)}**"
    return f"{heading}\n\n{str(message).strip()}"


def empty_state_markdown(message: str, action: str = "") -> str:
    """Return empty-state markdown with optional next action."""
    text = f"**No data available.**\n\n{str(message).strip()}"
    if action:
        text = f"{text}\n\nNext step: {str(action).strip()}"
    return text


def summarize_data_quality_status(rows: Sequence[Mapping[str, object]] | pd.DataFrame, status_column: str = "status") -> DataQualitySummary:
    """Summarize status values from dashboard/data-quality rows."""
    if isinstance(rows, pd.DataFrame):
        statuses = rows[status_column].tolist() if status_column in rows.columns else []
    else:
        statuses = [row.get(status_column) for row in rows]

    counts: dict[str, int] = {}
    worst_status = "ok"
    for raw_status in statuses:
        status = normalize_status(str(raw_status))
        counts[status] = counts.get(status, 0) + 1
        if STATUS_ORDER[status] > STATUS_ORDER[worst_status]:
            worst_status = status

    total = sum(counts.values())
    headline = "No status rows available." if total == 0 else f"{total} status row(s); worst status: {status_label(worst_status)}."
    return DataQualitySummary(total=total, counts=counts, worst_status=worst_status, headline=headline)


def render_section_header(st_module, title: str, subtitle: str = "", status: str | None = None) -> None:
    """Render a consistent section header in Streamlit."""
    st_module.markdown(section_header_markdown(title, subtitle=subtitle, status=status))


def render_metric_card(st_module, card: MetricCard) -> None:
    """Render a compact metric card in Streamlit."""
    st_module.markdown(metric_card_markdown(card))


def render_callout(st_module, message: str, level: str = "info", title: str = "") -> None:
    """Render a callout using native Streamlit status methods."""
    body = callout_markdown(message, level=level, title=title)
    normalized = normalize_status(level)
    if normalized in {"warning", "sample", "limited", "missing"}:
        st_module.warning(body)
    elif normalized in {"error", "invalid", "blocker", "skipped"}:
        st_module.error(body)
    elif normalized in {"ok", "ready", "available", "success"}:
        st_module.success(body)
    else:
        st_module.info(body)


def render_empty_state(st_module, message: str, action: str = "") -> None:
    """Render a user-facing empty state."""
    st_module.warning(empty_state_markdown(message, action=action))


def render_dataframe(st_module, table: pd.DataFrame) -> None:
    """Render a dataframe with the current Streamlit width API."""
    st_module.dataframe(table, width="stretch")


def table_shape_text(table: pd.DataFrame) -> str:
    """Return concise row/column context for a table."""
    return f"{len(table)} row(s), {len(table.columns)} column(s)"


def build_table_index(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Return a compact index for non-empty tables without rendering all rows."""
    rows = []
    for name, table in tables.items():
        if isinstance(table, pd.DataFrame) and not table.empty:
            rows.append(
                {
                    "table": str(name),
                    "rows": len(table),
                    "columns": len(table.columns),
                    "status": "available",
                }
            )
    return pd.DataFrame(rows)


def safe_display_text(value: object, fallback: str = "Not available") -> str:
    """Return display text without inventing unavailable values."""
    if value is None:
        return fallback
    try:
        missing = bool(pd.isna(value))
    except (TypeError, ValueError):
        missing = False
    if missing:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def html_escape_text(value: object) -> str:
    """Escape text for future card markup helpers."""
    return escape(safe_display_text(value))
