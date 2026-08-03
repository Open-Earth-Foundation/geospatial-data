#!/usr/bin/env python3
"""Export Hansen Global Forest Change tree cover 2000 for NBS mechanism screening.

Writes to ``hansen_forest_change/sites/{site}/data/output/{prefix}_hansen_treecover2000_30m.tif``,
matching ``nbs_screening/config/sites/{site}.yaml`` catalog paths.

Source: GEE ``UMD/hansen/global_forest_change_2024_v1_12`` band ``treecover2000`` (0–100%).

Examples:
  python transformation/hansen_forest_change/extract_treecover2000.py --site richfield
  python transformation/hansen_forest_change/extract_treecover2000.py --country "United States"
  python transformation/hansen_forest_change/extract_treecover2000.py --site richfield --qa-only
  python transformation/hansen_forest_change/extract_treecover2000.py --site richfield --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

HANSEN_ROOT = Path(__file__).resolve().parent
if str(HANSEN_ROOT) not in sys.path:
    sys.path.insert(0, str(HANSEN_ROOT))

from input_common import (  # noqa: E402
    CRS,
    EE_BAND,
    EE_IMAGE,
    SCALE_M,
    init_ee,
    load_hansen_site,
    load_site_roi,
    reexec_with_repo_venv_if_needed,
    resolve_site_slugs,
)
from qa_hansen import qa_hansen_treecover2000  # noqa: E402


@dataclass
class SiteRunResult:
    site: str
    display_name: str
    ok: bool
    error: str | None = None
    output: str | None = None


def run(
    site: str,
    *,
    authenticate: bool = False,
    write_qa: bool = True,
    qa_only: bool = False,
    dry_run: bool = False,
) -> SiteRunResult:
    cfg = load_hansen_site(site)
    display = str(cfg.get("display_name") or site)
    out_path = Path(cfg["hansen_output_path"])

    if dry_run:
        print(f"  would export → {out_path}")
        return SiteRunResult(site=site, display_name=display, ok=True, output=str(out_path))

    if not qa_only:
        reexec_with_repo_venv_if_needed("numpy", "rasterio")
        from gee_local_export import export_image_to_input  # noqa: E402

        ee = init_ee(authenticate=authenticate)
        roi = load_site_roi(cfg, ee)
        print(f"Hansen treecover2000 → {display} ({site})")
        treecover = (
            ee.Image(EE_IMAGE)
            .select(EE_BAND)
            .clip(roi)
            .reproject(crs=CRS, scale=SCALE_M)
            .toByte()
        )
        export_image_to_input(
            treecover,
            filename=out_path.name,
            region=roi,
            scale=SCALE_M,
            input_dir=out_path.parent,
            crs=CRS,
            description=out_path.stem,
            drive_folder="gee_exports",
        )
    elif not out_path.is_file():
        raise FileNotFoundError(f"Missing GeoTIFF for --qa-only: {out_path}")

    print(f"Output: {out_path}")
    if write_qa:
        qa_hansen_treecover2000(out_path, cfg, display=display)
        print(f"QA SVGs: {cfg['hansen_qa_dir_abs']}")

    return SiteRunResult(site=site, display_name=display, ok=True, output=str(out_path.resolve()))


def _resolve_sites(args: argparse.Namespace) -> list[str]:
    selection_flags = sum(
        bool(x)
        for x in (
            args.site,
            args.sites,
            args.all_configured,
            args.country,
        )
    )
    if selection_flags > 1:
        raise ValueError("Use only one of --site, --sites, --all-configured, --country")

    exclude: tuple[str, ...] = tuple(
        s.strip()
        for part in (args.exclude or [])
        for s in part.split(",")
        if s.strip()
    )

    if args.sites:
        return resolve_site_slugs(sites_csv=args.sites, exclude=exclude)
    if args.all_configured:
        return resolve_site_slugs(all_configured=True, exclude=exclude)
    if args.country:
        return resolve_site_slugs(country=args.country, exclude=exclude)
    if args.site:
        return resolve_site_slugs(site=args.site, exclude=exclude)
    return resolve_site_slugs(
        site=os.environ.get("NBS_SITE") or os.environ.get("FLOODS_SITE", "porto_alegre"),
        exclude=exclude,
    )


def _print_summary(results: list[SiteRunResult]) -> None:
    print("\n=== Hansen treecover2000 export summary ===")
    for row in results:
        status = "OK" if row.ok else f"FAIL ({row.error})"
        print(f"  {row.site:<14} {status}")
        if row.ok and row.output:
            print(f"    {row.output}")
    ok_n = sum(1 for r in results if r.ok)
    print(f"\nCompleted {ok_n}/{len(results)} sites.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", help="Single city slug")
    parser.add_argument("--sites", help="Comma-separated city slugs")
    parser.add_argument(
        "--all-configured",
        action="store_true",
        help="All cities with nbs_screening/config/sites/{slug}.yaml",
    )
    parser.add_argument(
        "--country",
        help='Filter by NBS site YAML country (e.g. "United States")',
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Skip site slug(s); repeat or comma-separate",
    )
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true")
    parser.add_argument("--qa-only", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        sites = _resolve_sites(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not sites:
        print("ERROR: no sites selected.", file=sys.stderr)
        return 1

    print(f"Sites ({len(sites)}): {', '.join(sites)}")
    results: list[SiteRunResult] = []
    for i, site in enumerate(sites, start=1):
        print(f"\n[{i}/{len(sites)}] {site}")
        try:
            results.append(
                run(
                    site,
                    authenticate=args.authenticate,
                    write_qa=not args.no_qa,
                    qa_only=args.qa_only,
                    dry_run=args.dry_run,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                SiteRunResult(site=site, display_name=site, ok=False, error=str(exc))
            )
            print(f"  ERROR: {exc}", file=sys.stderr)
            if not args.continue_on_error and not args.dry_run:
                break

    _print_summary(results)
    if len(results) == 1 and results[0].ok and not args.dry_run:
        print(
            "\nNext: python transformation/nbs_screening/check_nbs_layers.py "
            f"--site {results[0].site} --hazard heat"
        )
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
