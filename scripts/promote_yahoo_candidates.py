from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.yahoo_candidate_promotion import promote_reviewed_yahoo_candidates  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and optionally promote reviewed Yahoo-derived candidate CSVs. "
            "Dry-run is the default; use --apply only after manual review."
        )
    )
    parser.add_argument("--candidate-dir", default="data/reference/generated", help="Directory containing generated Yahoo candidate CSV files.")
    parser.add_argument("--output-dir", default="data/reference", help="Production reference output directory.")
    parser.add_argument("--config", default="config/data_sources.yaml", help="Path to data_sources.yaml for ticker coverage reporting.")
    parser.add_argument("--backup-dir", default=None, help="Optional backup directory. Defaults to <output-dir>/backups.")
    parser.add_argument("--apply", action="store_true", help="Actually write production CSVs after validation passes.")
    parser.add_argument(
        "--accepted-status",
        action="append",
        default=None,
        help="Accepted review status. Defaults to Reviewed and Approved. Can be supplied more than once.",
    )
    parser.add_argument(
        "--allow-blank-field",
        action="append",
        default=[],
        help="Important field allowed to be blank. Use sparingly after manual review.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    accepted = args.accepted_status or ["Reviewed", "Approved"]
    try:
        plan = promote_reviewed_yahoo_candidates(
            candidate_dir=args.candidate_dir,
            output_dir=args.output_dir,
            config_path=args.config,
            apply=args.apply,
            accepted_statuses=accepted,
            allow_blank_fields=args.allow_blank_field,
            backup_dir=args.backup_dir,
        )
    except ValueError as exc:
        print(f"Promotion blocked: {exc}", file=sys.stderr)
        return 2

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"Yahoo candidate promotion {mode}.")
    print("\nValidation report:")
    print(_format_table(plan.validation_report))
    print("\nTicker coverage report:")
    print(_format_table(plan.coverage_report))
    if args.apply:
        print("\nBackups:")
        print(_format_mapping(plan.backups))
        print("\nWritten production files:")
        print(_format_mapping(plan.written_paths))
    else:
        print("\nNo production files were written. Re-run with --apply after fixing validation errors and reviewing coverage gaps.")
    return 1 if plan.has_errors else 0


def _format_table(table) -> str:
    if table is None or table.empty:
        return "<no rows>"
    return table.to_string(index=False)


def _format_mapping(values: dict[str, Path]) -> str:
    if not values:
        return "<none>"
    return "\n".join(f"- {key}: {path}" for key, path in values.items())


if __name__ == "__main__":
    raise SystemExit(main())
