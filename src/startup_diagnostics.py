from __future__ import annotations

from dataclasses import dataclass
from importlib import util


YFINANCE_INSTALL_COMMAND = r".\.venv\Scripts\python.exe -m pip install -r requirements.txt"
STREAMLIT_VENV_RUN_COMMAND = r".\.venv\Scripts\python.exe -m streamlit run app.py"


@dataclass(frozen=True)
class DependencyDiagnostic:
    """Import availability diagnostic for a dashboard runtime dependency."""

    package: str
    importable: bool
    summary: str
    fix_commands: tuple[str, ...] = ()


def check_yfinance_available(find_spec=util.find_spec) -> DependencyDiagnostic:
    """Check whether yfinance is importable in the active Python environment."""
    importable = find_spec("yfinance") is not None
    if importable:
        return DependencyDiagnostic(
            package="yfinance",
            importable=True,
            summary="yfinance is available in this Python environment.",
        )
    return DependencyDiagnostic(
        package="yfinance",
        importable=False,
        summary="yfinance is not importable in this Python environment. Yahoo historical loading is unavailable until dependencies are installed.",
        fix_commands=(YFINANCE_INSTALL_COMMAND, STREAMLIT_VENV_RUN_COMMAND),
    )


def yfinance_missing_guidance(diagnostic: DependencyDiagnostic) -> str:
    """Return user-facing guidance for missing yfinance dependency."""
    if diagnostic.importable:
        return diagnostic.summary
    commands = "\n".join(diagnostic.fix_commands)
    return (
        f"{diagnostic.summary}\n\n"
        "Run Streamlit with the project virtual environment:\n\n"
        f"{commands}"
    )
