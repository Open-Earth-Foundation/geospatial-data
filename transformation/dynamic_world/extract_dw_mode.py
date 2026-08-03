#!/usr/bin/env python3
"""Export Dynamic World annual mode land-cover for NBS mechanism screening.

Writes NBS catalog rasters under ``dynamic_world/sites/{site}/data/output/``:

  - ``{prefix}_dynamicworld_{year}.tif`` — 10 m annual mode (``dynamic_world``)
  - ``{prefix}_dw_mode_250m_{year}.tif`` — 250 m mode aligned to NBS flood grid
  - copies 10 m raster to ``landslide_hazard/.../data/input/{prefix}_dw_mode_{year}.tif``

Examples:
  python transformation/dynamic_world/extract_dw_mode.py --site richfield
  python transformation/dynamic_world/extract_dw_mode.py --country "United States"
  python transformation/dynamic_world/extract_dw_mode.py --site richfield --only mode_10m,mode_250m
  python transformation/dynamic_world/extract_dw_mode.py --site richfield --dry-run
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

DW_ROOT = Path(__file__).resolve().parent
if str(DW_ROOT) not in sys.path:
    sys.path.insert(0, str(DW_ROOT))

from input_common import (  # noqa: E402
    CRS,
    DEFAULT_DW_YEAR,
    EE_COLLECTION,
    SCALE_10M,
    SCALE_250M,
    init_ee,
    load_dw_site,
    load_site_roi,
    reexec_with_repo_venv_if_needed,
    resolve_site_slugs,
)
from qa_dw import qa_dw_mode_10m, qa_dw_mode_250m  # noqa: E402

ProductKey = Literal["mode_10m", "mode_250m", "landslide"]
DEFAULT_ORDER: tuple[ProductKey, ...] = ("mode_10m", "mode_250m", "landslide")


@dataclass
class SiteRunResult:
    site: str
    display_name: str
    ok: bool
    error: str | None = None
    outputs: dict[str, str] = field(default_factory=dict)


def _build_dw_mode(ee: Any, roi: Any, year: int) -> Any:
    return (
        ee.ImageCollection(EE_COLLECTION)
        .select("label")
        .filterBounds(roi)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .mode()
        .clip(roi)
    )


def _export_mode(
    ee: Any,
    roi: Any,
    *,
    year: int,
    scale: int,
    out_path: Path,
    description: str,
) -> Path:
    from gee_local_export import export_image_to_input  # noqa: E402

    img = _build_dw_mode(ee, roi, year).reproject(crs=CRS, scale=scale).toUint8()
    export_image_to_input(
        img,
        filename=out_path.name,
        region=roi,
        scale=scale,
        input_dir=out_path.parent,
        crs=CRS,
        description=description,
        drive_folder="gee_exports",
    )
    return out_path


def _sync_landslide_input(cfg: dict[str, Any]) -> Path:
    src = Path(cfg["dw_mode_10m_path"])
    dst = Path(cfg["dw_landslide_path"])
    if not src.is_file():
        raise FileNotFoundError(f"Missing 10 m mode raster for landslide sync: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.samefile(src):
        return dst
    shutil.copy2(src, dst)
    print(f"Copied 10 m mode → landslide input: {dst}")
    return dst


def run(
    site: str,
    *,
    products: tuple[ProductKey, ...] = DEFAULT_ORDER,
    dw_year: int = DEFAULT_DW_YEAR,
    authenticate: bool = False,
    write_qa: bool = True,
    qa_only: bool = False,
    dry_run: bool = False,
) -> SiteRunResult:
    cfg = load_dw_site(site, dw_year=dw_year)
    display = str(cfg.get("display_name") or site)
    outputs: dict[str, str] = {}

    paths = {
        "mode_10m": Path(cfg["dw_mode_10m_path"]),
        "mode_250m": Path(cfg["dw_mode_250m_path"]),
        "landslide": Path(cfg["dw_landslide_path"]),
    }

    if dry_run:
        for key in products:
            print(f"  would write [{key}] → {paths[key]}")
        return SiteRunResult(
            site=site,
            display_name=display,
            ok=True,
            outputs={k: str(paths[k]) for k in products},
        )

    ee = None
    roi = None
    needs_gee = qa_only is False and any(k in products for k in ("mode_10m", "mode_250m"))

    if needs_gee:
        reexec_with_repo_venv_if_needed("numpy", "rasterio")
        ee = init_ee(authenticate=authenticate)
        roi = load_site_roi(cfg, ee)
        print(f"Dynamic World mode → {display} ({site}) · year {dw_year}")

    if "mode_10m" in products:
        out = paths["mode_10m"]
        if not qa_only:
            _export_mode(
                ee,
                roi,
                year=dw_year,
                scale=SCALE_10M,
                out_path=out,
                description=out.stem,
            )
        elif not out.is_file():
            raise FileNotFoundError(f"Missing GeoTIFF for --qa-only: {out}")
        outputs["mode_10m"] = str(out.resolve())
        print(f"10 m mode: {out}")
        if write_qa:
            qa_dw_mode_10m(out, cfg, display=display)

    if "mode_250m" in products:
        out = paths["mode_250m"]
        if not qa_only:
            _export_mode(
                ee,
                roi,
                year=dw_year,
                scale=SCALE_250M,
                out_path=out,
                description=out.stem,
            )
        elif not out.is_file():
            raise FileNotFoundError(f"Missing GeoTIFF for --qa-only: {out}")
        outputs["mode_250m"] = str(out.resolve())
        print(f"250 m mode: {out}")
        if write_qa:
            qa_dw_mode_250m(out, cfg, display=display)

    if "landslide" in products:
        if qa_only:
            out = paths["landslide"]
            if not out.is_file():
                raise FileNotFoundError(f"Missing landslide input for --qa-only: {out}")
        else:
            out = _sync_landslide_input(cfg)
        outputs["landslide"] = str(out.resolve())

    if write_qa and not dry_run:
        print(f"QA SVGs: {cfg['dw_qa_dir_abs']}")

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
        site=os.environ.get("NBS_SITE")
        or os.environ.get("LANDSLIDES_SITE")
        or os.environ.get("FLOODS_SITE", "porto_alegre"),
        exclude=exclude,
    )


def _parse_products(raw: str | None) -> tuple[ProductKey, ...]:
    if not raw:
        return DEFAULT_ORDER
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    valid = set(DEFAULT_ORDER)
    unknown = [k for k in keys if k not in valid]
    if unknown:
        raise ValueError(f"Unknown products: {unknown}. Valid: {', '.join(DEFAULT_ORDER)}")
    return tuple(keys)


def _print_summary(results: list[SiteRunResult]) -> None:
    print("\n=== Dynamic World export summary ===")
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
        help=f"Comma-separated subset of: {','.join(DEFAULT_ORDER)}",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help=f"Dynamic World composite year (default: site dw_year or {DEFAULT_DW_YEAR})",
    )
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true")
    parser.add_argument("--qa-only", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        sites = _resolve_sites(args)
        products = _parse_products(args.only)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not sites:
        print("ERROR: no sites selected.", file=sys.stderr)
        return 1

    print(f"Sites ({len(sites)}): {', '.join(sites)}")
    print(f"Products: {', '.join(products)}")

    results: list[SiteRunResult] = []
    for i, site in enumerate(sites, start=1):
        print(f"\n[{i}/{len(sites)}] {site}")
        try:
            year = args.year if args.year is not None else int(load_dw_site(site)["dw_year"])
            results.append(
                run(
                    site,
                    products=products,
                    dw_year=year,
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
