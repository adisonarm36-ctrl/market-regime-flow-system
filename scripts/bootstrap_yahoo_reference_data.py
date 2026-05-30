from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.yahoo_reference_bootstrap import (  # noqa: E402
    bootstrap_yahoo_reference_candidates,
    build_promotion_review_report,
    configured_yahoo_tickers,
    load_asset_hint_map,
    read_candidate_outputs,
    write_candidate_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Yahoo-derived reference-data candidates for manual review. "
            "Outputs are local artifacts only and must not be treated as verified production reference data."
        )
    )
    parser.add_argument("--config", default="config/data_sources.yaml", help="Path to data_sources.yaml.")
    parser.add_argument("--output-dir", default="data/reference/generated", help="Directory for generated candidate CSV files.")
    parser.add_argument("--tickers", nargs="*", help="Optional Yahoo tickers. Defaults to configured yahoo.tickers.")
    parser.add_argument("--asset-hints", default="data/reference/asset_map_sample.csv", help="Optional existing/sample asset map used only as review hints.")
    parser.add_argument("--validate-existing", action="store_true", help="Read existing generated candidates and print the manual-promotion review report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    if args.validate_existing:
        result = read_candidate_outputs(output_dir)
        print(build_promotion_review_report(result).to_string(index=False))
        return 0

    tickers = args.tickers or configured_yahoo_tickers(args.config)
    if not tickers:
        print("No Yahoo tickers provided or configured. Add tickers or pass --tickers.", file=sys.stderr)
        return 2

    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:
        print("yfinance is not importable. Install project requirements before running this bootstrap.", file=sys.stderr)
        raise SystemExit(2) from exc

    result = bootstrap_yahoo_reference_candidates(
        tickers=tickers,
        yfinance_module=yf,
        asset_hint_map=load_asset_hint_map(args.asset_hints),
    )
    written = write_candidate_outputs(result, output_dir)
    print("Yahoo-derived candidate files written. Review before manual promotion:")
    for label, path in written.items():
        print(f"- {label}: {path}")
    print()
    print(build_promotion_review_report(result).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
