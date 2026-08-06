#!/usr/bin/env python3
"""Batch landslide mechanism pipeline for configured NBS screening cities (L4).

Per site: mechanism input extract (optional) → grid compute → COG/tiles publish.

Example:
  python transformation/nbs_screening/landslide/batch_mechanism.py --site richfield
  python transformation/nbs_screening/landslide/batch_mechanism.py --country "United States"
  python transformation/nbs_screening/landslide/batch_mechanism.py \\
    --all-configured --upload --write-catalog --continue-on-error
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

LANDSLIDE_ROOT = Path(__file__).resolve().parent
NBS_ROOT = LANDSLIDE_ROOT.parent
for _path in (LANDSLIDE_ROOT, NBS_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from catalog_layers import HAZARD_REQUIRED_LAYERS, get_layer_sources  # noqa: E402
from compute_mechanism import compute_landslide_mechanism  # noqa: E402
from extract_common import runner_python  # noqa: E402
from publish_mechanism import run_publish  # noqa: E402
from site_config import (  # noqa: E402
    list_configured_sites,
    load_site_config,
    merged_catalog_entries,
    resolve_site_slugs,
)

StepName = Literal["inputs", "compute", "publish"]
StepStatus = Literal["ok", "skipped", "failed"]
HAZARD = "landslide"


@dataclass
class SiteResult:
    site: str
    display_name: str
    steps: dict[StepName, StepStatus] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and all(s != "failed" for s in self.steps.values())


def _preflight(site: str) -> dict[str, Any]:
    cfg = load_site_config(site)
    sources = get_layer_sources(HAZARD, site)
    entries = merged_catalog_entries(cfg, HAZARD)
    missing_layers = [key for key in entries if key not in sources]
    missing_required = [
        layer for layer in HAZARD_REQUIRED_LAYERS[HAZARD] if layer not in sources
    ]
    return {
        "display_name": str(cfg.get("display_name") or site),
        "country": str(cfg.get("country") or ""),
        "missing_layers": missing_layers,
        "missing_required": missing_required,
    }


def _run_inputs_extract(site: str, *, dry_run: bool) -> tuple[StepStatus, str | None]:
    cmd = [
        runner_python(),
        str(LANDSLIDE_ROOT / "extract_mechanism_inputs.py"),
        "--site",
        site,
    ]
    if dry_run:
        print(f"  [dry-run] {' '.join(cmd)}")
        return "skipped", None
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        return "failed", f"extract_mechanism_inputs exited {proc.returncode}"
    return "ok", None


def run_site_pipeline(
    site: str,
    *,
    extract_inputs: bool,
    extract_if_missing: bool,
    skip_inputs: bool,
    skip_compute: bool,
    skip_publish: bool,
    publish_build: bool,
    upload: bool,
    write_catalog: bool,
    dry_run: bool,
) -> SiteResult:
    pre = _preflight(site)
    result = SiteResult(site=site, display_name=pre["display_name"])

    if pre["missing_required"]:
        result.error = f"missing required layers: {pre['missing_required']}"
        result.steps = {"inputs": "skipped", "compute": "skipped", "publish": "skipped"}
        return result

    need_inputs = not skip_inputs and (
        extract_inputs or (extract_if_missing and bool(pre["missing_layers"]))
    )
    if skip_inputs:
        result.steps["inputs"] = "skipped"
    elif need_inputs:
        status, error = _run_inputs_extract(site, dry_run=dry_run)
        result.steps["inputs"] = status
        if status == "failed":
            result.error = f"inputs: {error}"
            result.steps["compute"] = "skipped"
            result.steps["publish"] = "skipped"
            return result
    else:
        if pre["missing_layers"]:
            print(f"  WARNING: missing optional layers {pre['missing_layers']}")
        result.steps["inputs"] = "skipped"

    if skip_compute:
        result.steps["compute"] = "skipped"
    elif dry_run:
        print(f"  [dry-run] compute_landslide_mechanism --site {site}")
        result.steps["compute"] = "skipped"
    else:
        try:
            compute_landslide_mechanism(site, aoi="boundary")
            result.steps["compute"] = "ok"
        except Exception as exc:  # noqa: BLE001
            result.steps["compute"] = "failed"
            result.error = f"compute: {exc}"
            result.steps["publish"] = "skipped"
            return result

    if skip_publish:
        result.steps["publish"] = "skipped"
    elif dry_run:
        flags = []
        if publish_build:
            flags.append("--build")
        if upload:
            flags.append("--upload")
        if write_catalog:
            flags.append("--write-catalog")
        print(f"  [dry-run] publish_mechanism --site {site} {' '.join(flags)}".strip())
        result.steps["publish"] = "skipped"
    else:
        try:
            run_publish(
                site,
                build=publish_build,
                upload=upload,
                write_catalog=write_catalog,
            )
            result.steps["publish"] = "ok"
        except Exception as exc:  # noqa: BLE001
            result.steps["publish"] = "failed"
            result.error = f"publish: {exc}"
            return result

    return result


def _print_summary(results: list[SiteResult]) -> None:
    print("\n=== Landslide batch summary ===")
    print(f"{'Site':<14} {'Inputs':<8} {'Compute':<8} {'Publish':<8} Status")
    for row in results:
        status = "OK" if row.ok else f"FAIL ({row.error})"
        print(
            f"{row.site:<14} "
            f"{row.steps.get('inputs', '?'):<8} "
            f"{row.steps.get('compute', '?'):<8} "
            f"{row.steps.get('publish', '?'):<8} "
            f"{status}"
        )
    ok_n = sum(1 for r in results if r.ok)
    print(f"\nCompleted {ok_n}/{len(results)} sites successfully.")


def run_batch(
    sites: list[str],
    *,
    extract_inputs: bool,
    extract_if_missing: bool,
    skip_inputs: bool,
    skip_compute: bool,
    skip_publish: bool,
    publish_build: bool,
    upload: bool,
    write_catalog: bool,
    continue_on_error: bool,
    dry_run: bool,
) -> list[SiteResult]:
    results: list[SiteResult] = []
    for i, site in enumerate(sites, start=1):
        pre = _preflight(site)
        print(f"\n[{i}/{len(sites)}] {pre['display_name']} ({site})")
        if pre.get("country"):
            print(f"  country: {pre['country']}")
        if pre["missing_required"]:
            print(f"  SKIP: missing required layers {pre['missing_required']}")
        elif pre["missing_layers"]:
            print(f"  missing catalog layers: {pre['missing_layers']}")
        else:
            print("  catalog layers: ready")

        try:
            result = run_site_pipeline(
                site,
                extract_inputs=extract_inputs,
                extract_if_missing=extract_if_missing,
                skip_inputs=skip_inputs,
                skip_compute=skip_compute,
                skip_publish=skip_publish,
                publish_build=publish_build,
                upload=upload,
                write_catalog=write_catalog,
                dry_run=dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            result = SiteResult(
                site=site,
                display_name=pre["display_name"],
                steps={"inputs": "failed", "compute": "failed", "publish": "failed"},
                error=str(exc),
            )
            if not dry_run:
                traceback.print_exc()

        results.append(result)
        if not result.ok and not continue_on_error and not dry_run:
            print(f"\nStopping batch after failure on {site}. Use --continue-on-error to proceed.")
            break

    _print_summary(results)
    return results


def _resolve_batch_sites(args: argparse.Namespace) -> list[str]:
    if args.all_configured:
        return resolve_site_slugs(all_configured=True, exclude=tuple(args.exclude))
    if args.country:
        return resolve_site_slugs(country=args.country, exclude=tuple(args.exclude))
    if args.sites:
        return resolve_site_slugs(sites_csv=args.sites, exclude=tuple(args.exclude))
    if args.site:
        return resolve_site_slugs(site=args.site, exclude=tuple(args.exclude))
    return resolve_site_slugs(all_configured=True, exclude=tuple(args.exclude))


def main(argv: list[str] | None = None) -> int:
    configured = list_configured_sites()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", help="Single city slug")
    parser.add_argument(
        "--sites",
        help=f"Comma-separated city slugs (configured: {', '.join(configured)})",
    )
    parser.add_argument("--all-configured", action="store_true")
    parser.add_argument("--country", help='YAML country filter (e.g. "United States")')
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument(
        "--extract-inputs",
        action="store_true",
        help="Always run landslide/extract_mechanism_inputs.py before compute",
    )
    parser.add_argument(
        "--extract-if-missing",
        action="store_true",
        default=True,
        help="Run input extract when catalog layers are missing (default: True)",
    )
    parser.add_argument(
        "--no-extract-if-missing",
        action="store_false",
        dest="extract_if_missing",
    )
    parser.add_argument("--skip-inputs", action="store_true", help="Skip mechanism input extract")
    parser.add_argument("--skip-compute", action="store_true")
    parser.add_argument("--skip-publish", action="store_true")
    parser.add_argument("--no-build", action="store_false", dest="publish_build")
    parser.set_defaults(publish_build=True)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--write-catalog", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    exclude: list[str] = []
    for item in args.exclude:
        exclude.extend(s.strip() for s in item.split(",") if s.strip())
    args.exclude = exclude

    selection_flags = sum(
        bool(x) for x in (args.site, args.sites, args.all_configured, args.country)
    )
    if selection_flags > 1:
        parser.error("Use only one of --site, --sites, --all-configured, --country")

    try:
        sites = _resolve_batch_sites(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not sites:
        print("ERROR: no sites selected.", file=sys.stderr)
        return 1

    print(f"Landslide pipeline sites ({len(sites)}): {', '.join(sites)}")
    results = run_batch(
        sites,
        extract_inputs=args.extract_inputs,
        extract_if_missing=args.extract_if_missing,
        skip_inputs=args.skip_inputs,
        skip_compute=args.skip_compute,
        skip_publish=args.skip_publish,
        publish_build=args.publish_build,
        upload=args.upload,
        write_catalog=args.write_catalog,
        continue_on_error=args.continue_on_error,
        dry_run=args.dry_run,
    )
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
