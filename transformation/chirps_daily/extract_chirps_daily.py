#!/usr/bin/env python3
"""Export CHIRPS daily extreme precipitation indices for NBS flood mechanism screening.

Writes NBS catalog rasters under ``chirps_daily/sites/{site}/data/output/``:

  - ``{prefix}_rx1day_{year}.tif`` — annual max 1-day precipitation (mm)
  - ``{prefix}_rx5day_{year}.tif`` — annual max 5-day rolling sum (mm)
  - ``{prefix}_r90p_{year}.tif`` — 90th percentile of daily precipitation (mm)

Source: GEE ``UCSB-CHG/CHIRPS/DAILY`` band ``precipitation``.

Examples:
  python transformation/chirps_daily/extract_chirps_daily.py --site richfield
  python transformation/chirps_daily/extract_chirps_daily.py --country "United States"
  python transformation/chirps_daily/extract_chirps_daily.py --site richfield --only rx1day,rx5day
  python transformation/chirps_daily/extract_chirps_daily.py --site richfield --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CHIRPS_ROOT = Path(__file__).resolve().parent
if str(CHIRPS_ROOT) not in sys.path:
    sys.path.insert(0, str(CHIRPS_ROOT))

from input_common import (  # noqa: E402
    CHIRPS_LAYERS,
    COMPUTE_FNS,
    CRS,
    DEFAULT_YEAR,
    SCALE_M,
    ChirpsLayer,
    daily_collection,
    init_ee,
    load_chirps_site,
    load_site_roi,
    reexec_with_repo_venv_if_needed,
    resolve_site_slugs,
)
from qa_chirps import QA_BY_LAYER  # noqa: E402

DEFAULT_ORDER: tuple[ChirpsLayer, ...] = CHIRPS_LAYERS


@dataclass
class SiteRunResult:
    site: str
    display_name: str
    ok: bool
    error: str | None = None
    outputs: dict[str, str] = field(default_factory=dict)


def _export_layer(
    image: Any,
    *,
    out_path: Path,
    roi: Any,
) -> Path:
    from gee_local_export import export_image_to_input  # noqa: E402

    export_image_to_input(
        image.clip(roi).reproject(crs=CRS, scale=SCALE_M).toFloat(),
        filename=out_path.name,
        region=roi,
        scale=SCALE_M,
        input_dir=out_path.parent,
        crs=CRS,
        description=out_path.stem,
        drive_folder="gee_exports",
    )
    return out_path


def run(
    site: str,
    *,
    layers: tuple[ChirpsLayer, ...] = DEFAULT_ORDER,
    year: int = DEFAULT_YEAR,
    authenticate: bool = False,
    write_qa: bool = True,
    qa_only: bool = False,
    dry_run: bool = False,
) -> SiteRunResult:
    cfg = load_chirps_site(site, year=year)
    display = str(cfg.get("display_name") or site)
    paths = {layer: Path(cfg["chirps_paths"][layer]) for layer in CHIRPS_LAYERS}
    outputs: dict[str, str] = {}

    if dry_run:
        for layer in layers:
            print(f"  would write [{layer}] → {paths[layer]}")
        return SiteRunResult(
            site=site,
            display_name=display,
            ok=True,
            outputs={layer: str(paths[layer]) for layer in layers},
        )

    chirps = None
    roi = None
    ee = None
    if not qa_only:
        reexec_with_repo_venv_if_needed("numpy", "rasterio")
        ee = init_ee(authenticate=authenticate)
        roi = load_site_roi(cfg, ee)
        chirps = daily_collection(ee, roi, year=year)
        count = chirps.size().getInfo()
        print(f"CHIRPS daily → {display} ({site}) · {year} · {count} days")
        if count < 5 and "rx5day" in layers:
            raise ValueError(f"Need at least 5 daily images for RX5day; got {count}")

    for layer in layers:
        out = paths[layer]
        if not qa_only:
            image = COMPUTE_FNS[layer](chirps, ee)
            _export_layer(image, out_path=out, roi=roi)
        elif not out.is_file():
            raise FileNotFoundError(f"Missing GeoTIFF for --qa-only: {out}")
        outputs[layer] = str(out.resolve())
        print(f"{layer}: {out}")
        if write_qa:
            QA_BY_LAYER[layer](out, cfg, display=display)

    if write_qa and not dry_run:
        print(f"QA SVGs: {cfg['chirps_qa_dir_abs']}")

    return SiteRunResult(site=site, display_name=display, ok=True, outputs=outputs)


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


def _parse_layers(raw: str | None) -> tuple[ChirpsLayer, ...]:
    if not raw:
        return DEFAULT_ORDER
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    valid = set(CHIRPS_LAYERS)
    unknown = [k for k in keys if k not in valid]
    if unknown:
        raise ValueError(f"Unknown layers: {unknown}. Valid: {', '.join(CHIRPS_LAYERS)}")
    return tuple(keys)  # type: ignore[return-value]


def _print_summary(results: list[SiteRunResult]) -> None:
    print("\n=== CHIRPS daily export summary ===")
    for row in results:
        status = "OK" if row.ok else f"FAIL ({row.error})"
        print(f"  {row.site:<14} {status}")
        for key, path in row.outputs.items():
            print(f"    [{key}] {path}")
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
    parser.add_argument(
        "--only",
        default=None,
        help=f"Comma-separated subset of: {','.join(CHIRPS_LAYERS)}",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=DEFAULT_YEAR,
        help=f"Calendar year for indices (default: {DEFAULT_YEAR})",
    )
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true")
    parser.add_argument("--qa-only", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        sites = _resolve_sites(args)
        layers = _parse_layers(args.only)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not sites:
        print("ERROR: no sites selected.", file=sys.stderr)
        return 1

    print(f"Sites ({len(sites)}): {', '.join(sites)}")
    print(f"Layers: {', '.join(layers)} · year={args.year}")

    results: list[SiteRunResult] = []
    for i, site in enumerate(sites, start=1):
        print(f"\n[{i}/{len(sites)}] {site}")
        try:
            results.append(
                run(
                    site,
                    layers=layers,
                    year=args.year,
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
            f"--site {results[0].site} --hazard flood"
        )
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
