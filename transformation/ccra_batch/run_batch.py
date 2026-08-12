#!/usr/bin/env python3
"""CLI: multi-city CCRA batch from a single JSON input.

Examples:
  # Resolve + print plan for 5 Minnesota cities (no GEE work)
  python transformation/ccra_batch/run_batch.py \\
    --input docs/examples/ccra_batch_minnesota.json --dry-run

  # Parallel compute/risk for configured cities (keep max_workers low for EE)
  python transformation/ccra_batch/run_batch.py \\
    --input docs/examples/ccra_batch_minnesota.json \\
    --stages compute,acs,risk --jobs 2 --continue-on-error

  # Benchmark dry-run timing of orchestration for 5+ cities
  python transformation/ccra_batch/run_batch.py \\
    --input docs/examples/ccra_batch_minnesota.json --dry-run --jobs 1 \\
    --report /tmp/ccra_batch_seq.json
  python transformation/ccra_batch/run_batch.py \\
    --input docs/examples/ccra_batch_minnesota.json --dry-run --jobs 4 \\
    --report /tmp/ccra_batch_par.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "transformation") not in sys.path:
    sys.path.insert(0, str(ROOT / "transformation"))

from ccra_batch.config import (  # noqa: E402
    DEFAULT_HAZARDS,
    DEFAULT_STAGES,
    VALID_HAZARDS,
    VALID_STAGES,
    load_batch_config,
)
from ccra_batch.resolve import list_configured_slugs  # noqa: E402
from ccra_batch.runner import print_summary, run_batch, write_batch_report  # noqa: E402


def _parse_csv(value: str | None, *, valid: set[str], default: tuple[str, ...]) -> tuple[str, ...] | None:
    if value is None:
        return None
    items = [s.strip().lower() for s in value.split(",") if s.strip()]
    bad = [s for s in items if s not in valid]
    if bad:
        raise argparse.ArgumentTypeError(f"Invalid values {bad}; expected {sorted(valid)}")
    return tuple(items) if items else default


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run CCRA H/E/V/R pipeline for multiple cities from one JSON file.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        help="Batch JSON path (see docs/examples/ccra_batch_*.json)",
    )
    parser.add_argument(
        "--stages",
        help=f"Comma-separated stage override (default from JSON or {','.join(DEFAULT_STAGES)})",
    )
    parser.add_argument(
        "--hazards",
        help=f"Comma-separated hazard override (default from JSON or {','.join(DEFAULT_HAZARDS)})",
    )
    parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=None,
        help="Parallel city workers (overrides JSON options.max_workers)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        default=None,
        help="Continue after a city failure (default: JSON options or true)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop scheduling new cities after the first failure",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip stages whose primary output already exists",
    )
    parser.add_argument("--upload", action="store_true", help="Publish with --upload")
    parser.add_argument("--write-catalog", action="store_true", help="Publish with --write-catalog")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve cities, prepare regional cache, plan stages — do not execute CLIs",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Write JSON run report (timings, per-city status, efficiency_ratio)",
    )
    parser.add_argument(
        "--list-configured",
        action="store_true",
        help="Print configured flood_hazard site slugs and exit",
    )
    args = parser.parse_args(argv)

    if args.list_configured:
        print("Configured site slugs:")
        for slug in list_configured_slugs():
            print(f"  - {slug}")
        return 0

    if args.input is None:
        print("ERROR: --input is required unless --list-configured", file=sys.stderr)
        return 2
    if not args.input.is_file():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 2

    try:
        config = load_batch_config(args.input)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: invalid batch JSON: {exc}", file=sys.stderr)
        return 2

    if args.stages:
        try:
            config.stages = _parse_csv(args.stages, valid=VALID_STAGES, default=DEFAULT_STAGES)  # type: ignore[assignment]
        except argparse.ArgumentTypeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    if args.hazards:
        try:
            config.hazards = _parse_csv(args.hazards, valid=VALID_HAZARDS, default=DEFAULT_HAZARDS)  # type: ignore[assignment]
        except argparse.ArgumentTypeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    if args.skip_existing:
        config.options.skip_existing = True
    if args.upload:
        config.options.upload = True
    if args.write_catalog:
        config.options.write_catalog = True

    continue_on_error = config.options.continue_on_error
    if args.fail_fast:
        continue_on_error = False
    elif args.continue_on_error:
        continue_on_error = True

    print(f"Batch: {config.batch_id}  cities={config.n_cities}  region={config.region or '—'}")
    print(f"Stages: {', '.join(config.stages)}")
    print(f"Hazards: {', '.join(config.hazards)}")
    print(f"Configured sites available: {', '.join(list_configured_slugs())}")

    result = run_batch(
        config,
        dry_run=args.dry_run,
        max_workers=args.jobs,
        continue_on_error=continue_on_error,
    )
    print_summary(result)

    if args.report:
        write_batch_report(result, args.report)
        print(f"Wrote report: {args.report}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
