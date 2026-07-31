#!/usr/bin/env python3
"""Compute relative elevation & depression diagnostics from Copernicus DEM (N6).

Reads ``sites/<site>/data/input/<prefix>_dem_glo30_30m.tif`` (flood_hazard layout)
and writes screening rasters to ``sites/<site>/data/output/``:

  - ``<prefix>_relative_elevation_30m.tif`` (0–1, 1 = lowest)
  - ``<prefix>_depression_mask_30m.tif`` (0/1 sink mask)
  - ``<prefix>_depression_depth_30m.tif`` (m, priority-flood fill depth)

Example:
  python transformation/copernicus_dem/compute_dem_diagnostics.py --site richfield
  python transformation/copernicus_dem/compute_dem_diagnostics.py --all-configured
  python transformation/copernicus_dem/compute_dem_diagnostics.py --site edina --export-dem
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

COPERNICUS_DEM_ROOT = Path(__file__).resolve().parent
FLOOD_HAZARD_ROOT = COPERNICUS_DEM_ROOT.parent / "flood_hazard"
NBS_ROOT = COPERNICUS_DEM_ROOT.parent / "nbs_screening"

sys.path.insert(0, str(FLOOD_HAZARD_ROOT))

from dem_diagnostics_core import compute_dem_diagnostics_from_path  # noqa: E402
from input_common import init_ee, load_flood_site, load_site_roi  # noqa: E402


def _nbs_site_config():
    import importlib.util

    spec = importlib.util.spec_from_file_location("nbs_site_config", NBS_ROOT / "site_config.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load NBS site_config from {NBS_ROOT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reexec_with_repo_venv_if_needed(*modules: str) -> None:
    missing: list[str] = []
    for name in modules:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    if not missing:
        return
    repo_root = COPERNICUS_DEM_ROOT.parent.parent
    venv_py = repo_root / ".venv" / "bin" / "python"
    current = Path(sys.executable).resolve()
    if venv_py.is_file() and current != venv_py.resolve():
        print(
            f"NOTE: {', '.join(missing)} missing in {sys.executable}; "
            f"re-launching with {venv_py}",
            flush=True,
        )
        os.execv(str(venv_py), [str(venv_py), *sys.argv])
    raise SystemExit(f"ERROR: missing packages: {', '.join(missing)}")


@dataclass
class SiteRunResult:
    site: str
    display_name: str
    ok: bool
    error: str | None = None
    outputs: dict[str, str] | None = None


def _layer_paths(cfg: dict[str, Any]) -> dict[str, Path]:
    input_dir = Path(cfg["paths_abs"]["data_input"])
    output_dir = Path(cfg["paths_abs"]["data_output"])
    layers = cfg.get("layers") or {}
    return {
        "dem": input_dir / str(layers["dem"]),
        "relative_elevation": output_dir / str(layers["relative_elevation"]),
        "depression_mask": output_dir / str(layers["depression_mask"]),
        "depression_depth": output_dir / str(layers["depression_depth"]),
    }


def export_dem_from_gee(site: str, *, authenticate: bool = False) -> Path:
    reexec_with_repo_venv_if_needed("ee")
    from gee_local_export import export_image_to_input

    cfg = load_flood_site(site)
    paths = _layer_paths(cfg)
    ee = init_ee(authenticate=authenticate)
    roi = load_site_roi(cfg, ee)
    display = cfg.get("display_name") or site
    print(f"Exporting Copernicus DEM GLO-30 → {display} ({site})")
    dem = (
        ee.ImageCollection("COPERNICUS/DEM/GLO30")
        .select("DEM")
        .filterBounds(roi)
        .mosaic()
        .reproject(crs="EPSG:4326", scale=30)
        .clip(roi)
        .toFloat()
    )
    export_image_to_input(
        dem,
        filename=paths["dem"].name,
        region=roi,
        scale=30,
        input_dir=paths["dem"].parent,
        crs="EPSG:4326",
        description=paths["dem"].stem,
        drive_folder="gee_exports",
    )
    return paths["dem"]


def run_site(
    site: str,
    *,
    dem_path: Path | None = None,
    export_dem: bool = False,
    authenticate: bool = False,
    dry_run: bool = False,
) -> SiteRunResult:
    cfg = load_flood_site(site)
    display = str(cfg.get("display_name") or site)
    paths = _layer_paths(cfg)
    dem = Path(dem_path or paths["dem"])

    if dry_run:
        print(f"  [dry-run] DEM={dem}")
        for key in ("relative_elevation", "depression_mask", "depression_depth"):
            print(f"  [dry-run] out {key}={paths[key]}")
        if export_dem:
            print(f"  [dry-run] export_dem GEE → {paths['dem']}")
        return SiteRunResult(site=site, display_name=display, ok=True)

    if export_dem:
        export_dem_from_gee(site, authenticate=authenticate)
    elif not dem.is_file():
        raise FileNotFoundError(
            f"Missing DEM: {dem}. Run with --export-dem or place the GeoTIFF first."
        )

    print(f"Computing DEM diagnostics for {display} ({site})")
    print(f"  DEM: {dem}")
    result = compute_dem_diagnostics_from_path(
        dem,
        out_relative_elevation=paths["relative_elevation"],
        out_depression_mask=paths["depression_mask"],
        out_depression_depth=paths["depression_depth"],
    )
    sink_pct = 100.0 * result.sink_cells / max(result.valid_cells, 1)
    print(
        f"  valid={result.valid_cells:,} sinks={result.sink_cells:,} ({sink_pct:.2f}%)"
    )
    for key, path in (
        ("relative_elevation", result.relative_elevation),
        ("depression_mask", result.depression_mask),
        ("depression_depth", result.depression_depth),
    ):
        print(f"  wrote {key}: {path}")
    return SiteRunResult(
        site=site,
        display_name=display,
        ok=True,
        outputs={k: str(v) for k, v in paths.items() if k != "dem"},
    )


def _resolve_sites(args: argparse.Namespace) -> list[str]:
    nbs_sc = _nbs_site_config()
    resolve_site_slugs = nbs_sc.resolve_site_slugs
    exclude: list[str] = []
    for item in args.exclude:
        exclude.extend(s.strip() for s in item.split(",") if s.strip())
    args.exclude = exclude

    selection_flags = sum(
        bool(x) for x in (args.site, args.sites, args.all_configured, args.country)
    )
    if selection_flags > 1:
        raise ValueError("Use only one of --site, --sites, --all-configured, --country")

    if args.all_configured:
        return resolve_site_slugs(all_configured=True, exclude=tuple(exclude))
    if args.country:
        return resolve_site_slugs(country=args.country, exclude=tuple(exclude))
    if args.sites:
        return resolve_site_slugs(sites_csv=args.sites, exclude=tuple(exclude))
    if args.site:
        return resolve_site_slugs(site=args.site, exclude=tuple(exclude))
    return resolve_site_slugs(all_configured=True, exclude=tuple(exclude))


def _print_summary(results: list[SiteRunResult]) -> None:
    print("\n=== DEM diagnostics summary ===")
    for row in results:
        status = "OK" if row.ok else f"FAIL ({row.error})"
        print(f"  {row.site:<14} {status}")
    ok_n = sum(1 for r in results if r.ok)
    print(f"\nCompleted {ok_n}/{len(results)} sites.")


def main(argv: list[str] | None = None) -> int:
    reexec_with_repo_venv_if_needed("numpy", "rasterio")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", help="Single city slug")
    parser.add_argument("--sites", help="Comma-separated city slugs")
    parser.add_argument(
        "--all-configured",
        action="store_true",
        help="All cities with config/sites/{slug}.yaml (NBS registry)",
    )
    parser.add_argument("--country", help='Filter by NBS site YAML country (e.g. "United States")')
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Skip site slug(s); repeat or comma-separate",
    )
    parser.add_argument(
        "--export-dem",
        action="store_true",
        help="Export Copernicus DEM from GEE before computing (requires earthengine-api)",
    )
    parser.add_argument("--authenticate", action="store_true", help="Run ee.Authenticate() before export")
    parser.add_argument("--dem-path", type=Path, help="Override input DEM GeoTIFF path")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Process remaining cities after a failure",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned paths only")
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
                run_site(
                    site,
                    dem_path=args.dem_path,
                    export_dem=args.export_dem,
                    authenticate=args.authenticate,
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
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
