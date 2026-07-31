#!/usr/bin/env python3
"""Batch flood mechanism pipeline for configured NBS screening cities (N5).

Runs per site: OSM waterways extract (optional) → grid compute → COG/tiles publish.
Site list comes from ``config/sites/*.yaml`` — add a YAML to onboard a new city.

Example (all configured sites, local build):
  python transformation/nbs_screening/batch_flood_mechanism.py --all-configured

Example (United States cohort — current Minnesota cities):
  python transformation/nbs_screening/batch_flood_mechanism.py --country "United States"

Example (upload + catalog, continue on failure):
  python transformation/nbs_screening/batch_flood_mechanism.py \\
    --all-configured --upload --write-catalog --continue-on-error

Example (explicit subset):
  python transformation/nbs_screening/batch_flood_mechanism.py --sites richfield,edina
"""

from __future__ import annotations

import argparse
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

NBS_ROOT = Path(__file__).resolve().parent
if str(NBS_ROOT) not in sys.path:
    sys.path.insert(0, str(NBS_ROOT))

from catalog_layers import HAZARD_REQUIRED_LAYERS, get_layer_sources  # noqa: E402
from compute_nbs_mechanism import compute_flood_mechanism  # noqa: E402
from extract_osm_rivers import extract_osm_rivers  # noqa: E402
from nbs_mechanism_publish import run_publish  # noqa: E402
from site_config import (  # noqa: E402
    list_configured_sites,
    load_site_config,
    resolve_osm_rivers_path,
    resolve_site_slugs,
)

StepName = Literal["rivers", "compute", "publish"]
StepStatus = Literal["ok", "skipped", "failed"]


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
    sources = get_layer_sources("flood", site)
    missing_required = [layer for layer in HAZARD_REQUIRED_LAYERS["flood"] if layer not in sources]
    osm_path = resolve_osm_rivers_path(site)
    return {
        "display_name": str(cfg.get("display_name") or site),
        "country": str(cfg.get("country") or ""),
        "missing_required": missing_required,
        "osm_ready": osm_path is not None,
        "osm_path": str(osm_path) if osm_path else None,
    }


def run_site_pipeline(
    site: str,
    *,
    extract_rivers: bool,
    extract_if_missing: bool,
    river_buffer_m: float,
    skip_rivers: bool,
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
        result.steps = {"rivers": "skipped", "compute": "skipped", "publish": "skipped"}
        return result

    need_rivers = not skip_rivers and (extract_rivers or (extract_if_missing and not pre["osm_ready"]))
    if skip_rivers:
        result.steps["rivers"] = "skipped"
    elif need_rivers:
        if dry_run:
            print(f"  [dry-run] extract_osm_rivers --site {site} --buffer-m {river_buffer_m}")
            result.steps["rivers"] = "skipped"
        else:
            try:
                extract_osm_rivers(site, buffer_m=river_buffer_m)
                result.steps["rivers"] = "ok"
            except Exception as exc:  # noqa: BLE001
                result.steps["rivers"] = "failed"
                result.error = f"rivers: {exc}"
                result.steps["compute"] = "skipped"
                result.steps["publish"] = "skipped"
                return result
    else:
        if not pre["osm_ready"]:
            print(f"  WARNING: no OSM waterways for {site}; riverine uses fallback/missing path")
        result.steps["rivers"] = "skipped"

    if skip_compute:
        result.steps["compute"] = "skipped"
    elif dry_run:
        print(f"  [dry-run] compute_flood_mechanism --site {site}")
        result.steps["compute"] = "skipped"
    else:
        try:
            compute_flood_mechanism(site, aoi="boundary")
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
        print(f"  [dry-run] nbs_mechanism_publish --site {site} {' '.join(flags)}".strip())
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
    print("\n=== Batch summary ===")
    print(f"{'Site':<14} {'Rivers':<8} {'Compute':<8} {'Publish':<8} Status")
    for row in results:
        status = "OK" if row.ok else f"FAIL ({row.error})"
        print(
            f"{row.site:<14} "
            f"{row.steps.get('rivers', '?'):<8} "
            f"{row.steps.get('compute', '?'):<8} "
            f"{row.steps.get('publish', '?'):<8} "
            f"{status}"
        )
    ok_n = sum(1 for r in results if r.ok)
    print(f"\nCompleted {ok_n}/{len(results)} sites successfully.")


def run_batch(
    sites: list[str],
    *,
    extract_rivers: bool,
    extract_if_missing: bool,
    river_buffer_m: float,
    skip_rivers: bool,
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
        elif pre["osm_ready"]:
            print(f"  osm_waterways: {pre['osm_path']}")
        else:
            print("  osm_waterways: missing")

        try:
            result = run_site_pipeline(
                site,
                extract_rivers=extract_rivers,
                extract_if_missing=extract_if_missing,
                river_buffer_m=river_buffer_m,
                skip_rivers=skip_rivers,
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
                steps={"rivers": "failed", "compute": "failed", "publish": "failed"},
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
    parser.add_argument(
        "--all-configured",
        action="store_true",
        help="All cities with config/sites/{slug}.yaml (default when no site filter)",
    )
    parser.add_argument(
        "--country",
        help='Filter by YAML ``country`` field (e.g. "United States", "Brazil")',
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Skip site slug(s); repeat or comma-separate (e.g. --exclude porto_alegre)",
    )
    parser.add_argument(
        "--extract-rivers",
        action="store_true",
        help="Always extract OSM waterways before compute",
    )
    parser.add_argument(
        "--extract-if-missing",
        action="store_true",
        default=True,
        help="Extract OSM waterways when local file absent (default: True)",
    )
    parser.add_argument(
        "--no-extract-if-missing",
        action="store_false",
        dest="extract_if_missing",
        help="Do not auto-extract missing OSM waterways",
    )
    parser.add_argument("--skip-rivers", action="store_true", help="Skip OSM waterways extract")
    parser.add_argument("--skip-compute", action="store_true", help="Skip grid mechanism compute")
    parser.add_argument("--skip-publish", action="store_true", help="Skip COG/tiles publish step")
    parser.add_argument(
        "--no-build",
        action="store_false",
        dest="publish_build",
        help="Publish step: skip COG/tiles build (use existing out/)",
    )
    parser.set_defaults(publish_build=True)
    parser.add_argument("--upload", action="store_true", help="Upload COG/tiles/GeoJSON to S3")
    parser.add_argument(
        "--write-catalog",
        action="store_true",
        help="Write catalog/datasets.yaml (requires --upload for real URLs)",
    )
    parser.add_argument(
        "--river-buffer-m",
        type=float,
        default=3000.0,
        help="Overpass bbox buffer when extracting OSM waterways (default: 3000 m)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Process remaining cities after a site failure",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned steps only")
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
        print("ERROR: no sites selected after filters.", file=sys.stderr)
        return 1

    print(f"Batch sites ({len(sites)}): {', '.join(sites)}")

    results = run_batch(
        sites,
        extract_rivers=args.extract_rivers,
        extract_if_missing=args.extract_if_missing,
        river_buffer_m=args.river_buffer_m,
        skip_rivers=args.skip_rivers,
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
