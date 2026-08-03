#!/usr/bin/env python3
"""End-to-end flood NBS pipeline orchestrator (N7).

Per configured city, runs in order:

  1. DEM diagnostics (relative elevation + depression layers) — optional
  2. OSM waterways extract — optional
  3. Flood mechanism grid compute
  4. COG/tiles publish

Delegates to existing CLIs/modules (N4–N6). Does not upload DEM layers (see N8).

Example (single city, local build):
  python transformation/nbs_screening/run_nbs_flood_pipeline.py --site richfield

Example (Minnesota cohort, skip DEM when already computed):
  python transformation/nbs_screening/run_nbs_flood_pipeline.py \\
    --country "United States" --skip-dem

Example (prep only — DEM + rivers, no mechanism):
  python transformation/nbs_screening/run_nbs_flood_pipeline.py \\
    --sites richfield --skip-compute --skip-publish

Example (upload + catalog):
  python transformation/nbs_screening/run_nbs_flood_pipeline.py \\
    --all-configured --upload --write-catalog --continue-on-error
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

NBS_ROOT = Path(__file__).resolve().parent
COPERNICUS_DEM_ROOT = NBS_ROOT.parent / "copernicus_dem"

if str(NBS_ROOT) not in sys.path:
    sys.path.insert(0, str(NBS_ROOT))

from batch_flood_mechanism import (  # noqa: E402
    _preflight,
    _resolve_batch_sites,
    run_site_pipeline,
)
from site_config import list_configured_sites  # noqa: E402

StepName = Literal["dem", "rivers", "compute", "publish"]
StepStatus = Literal["ok", "skipped", "failed"]


@dataclass
class PipelineSiteResult:
    site: str
    display_name: str
    steps: dict[StepName, StepStatus] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and all(s != "failed" for s in self.steps.values())


def _run_dem_step(
    site: str,
    *,
    export_dem: bool,
    authenticate: bool,
    dem_path: Path | None,
    dry_run: bool,
) -> tuple[StepStatus, str | None]:
    cmd = [
        sys.executable,
        str(COPERNICUS_DEM_ROOT / "compute_dem_diagnostics.py"),
        "--site",
        site,
    ]
    if dry_run:
        cmd.append("--dry-run")
    if export_dem:
        cmd.append("--export-dem")
    if authenticate:
        cmd.append("--authenticate")
    if dem_path is not None:
        cmd.extend(["--dem-path", str(dem_path)])

    proc = subprocess.run(cmd, text=True)
    if proc.returncode != 0:
        return "failed", f"dem diagnostics exited {proc.returncode}"
    return ("skipped" if dry_run else "ok"), None


def run_site_flood_pipeline(
    site: str,
    *,
    skip_dem: bool,
    export_dem: bool,
    authenticate: bool,
    dem_path: Path | None,
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
) -> PipelineSiteResult:
    pre = _preflight(site)
    result = PipelineSiteResult(site=site, display_name=pre["display_name"])

    if skip_dem:
        result.steps["dem"] = "skipped"
    else:
        dem_status, dem_error = _run_dem_step(
            site,
            export_dem=export_dem,
            authenticate=authenticate,
            dem_path=dem_path,
            dry_run=dry_run,
        )
        result.steps["dem"] = dem_status
        if dem_status == "failed":
            result.error = dem_error
            result.steps["rivers"] = "skipped"
            result.steps["compute"] = "skipped"
            result.steps["publish"] = "skipped"
            return result

    mechanism = run_site_pipeline(
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
    for step in ("rivers", "compute", "publish"):
        result.steps[step] = mechanism.steps.get(step, "skipped")  # type: ignore[assignment]
    if mechanism.error:
        result.error = mechanism.error
    return result


def _print_summary(results: list[PipelineSiteResult]) -> None:
    print("\n=== Flood pipeline summary ===")
    print(f"{'Site':<14} {'DEM':<8} {'Rivers':<8} {'Compute':<8} {'Publish':<8} Status")
    for row in results:
        status = "OK" if row.ok else f"FAIL ({row.error})"
        print(
            f"{row.site:<14} "
            f"{row.steps.get('dem', '?'):<8} "
            f"{row.steps.get('rivers', '?'):<8} "
            f"{row.steps.get('compute', '?'):<8} "
            f"{row.steps.get('publish', '?'):<8} "
            f"{status}"
        )
    ok_n = sum(1 for r in results if r.ok)
    print(f"\nCompleted {ok_n}/{len(results)} sites successfully.")


def run_pipeline(
    sites: list[str],
    *,
    skip_dem: bool,
    export_dem: bool,
    authenticate: bool,
    dem_path: Path | None,
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
) -> list[PipelineSiteResult]:
    results: list[PipelineSiteResult] = []
    for i, site in enumerate(sites, start=1):
        pre = _preflight(site)
        print(f"\n[{i}/{len(sites)}] {pre['display_name']} ({site})")
        if pre.get("country"):
            print(f"  country: {pre['country']}")
        if pre["missing_required"]:
            print(f"  WARNING: missing required layers {pre['missing_required']} (compute may fail)")
        elif pre["osm_ready"]:
            print(f"  osm_waterways: {pre['osm_path']}")
        else:
            print("  osm_waterways: missing")

        try:
            result = run_site_flood_pipeline(
                site,
                skip_dem=skip_dem,
                export_dem=export_dem,
                authenticate=authenticate,
                dem_path=dem_path,
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
            result = PipelineSiteResult(
                site=site,
                display_name=pre["display_name"],
                steps={
                    "dem": "failed",
                    "rivers": "failed",
                    "compute": "failed",
                    "publish": "failed",
                },
                error=str(exc),
            )
            if not dry_run:
                traceback.print_exc()

        results.append(result)
        if not result.ok and not continue_on_error and not dry_run:
            print(f"\nStopping pipeline after failure on {site}. Use --continue-on-error to proceed.")
            break

    _print_summary(results)
    return results


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
    parser.add_argument("--skip-dem", action="store_true", help="Skip DEM diagnostics step")
    parser.add_argument(
        "--export-dem",
        action="store_true",
        help="Export Copernicus DEM from GEE before diagnostics (requires earthengine-api)",
    )
    parser.add_argument(
        "--authenticate",
        action="store_true",
        help="Run ee.Authenticate() before GEE DEM export",
    )
    parser.add_argument("--dem-path", type=Path, help="Override input DEM GeoTIFF path")
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

    print(f"Flood pipeline sites ({len(sites)}): {', '.join(sites)}")

    results = run_pipeline(
        sites,
        skip_dem=args.skip_dem,
        export_dem=args.export_dem,
        authenticate=args.authenticate,
        dem_path=args.dem_path,
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
