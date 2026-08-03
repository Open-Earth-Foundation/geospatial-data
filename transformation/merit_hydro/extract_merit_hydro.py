#!/usr/bin/env python3
"""Export MERIT Hydro UPA and ELV layers for NBS mechanism screening.

Writes NBS catalog rasters under ``merit_hydro/sites/{site}/data/output/``:

  - ``{prefix}_merit_hydro_upa_90m.tif`` — upstream drainage area (km²)
  - ``{prefix}_merit_hydro_elv_90m.tif`` — elevation (m)

Source: GEE ``MERIT/Hydro/v1_0_1`` bands ``upa``, ``elv``.
(HAND export remains ``extract_hand.py`` → landslide_hazard input.)

Examples:
  python transformation/merit_hydro/extract_merit_hydro.py --site richfield
  python transformation/merit_hydro/extract_merit_hydro.py --country "United States"
  python transformation/merit_hydro/extract_merit_hydro.py --site richfield --only upa
  python transformation/merit_hydro/extract_merit_hydro.py --site richfield --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MERIT_ROOT = Path(__file__).resolve().parent
if str(MERIT_ROOT) not in sys.path:
    sys.path.insert(0, str(MERIT_ROOT))

from input_common import (  # noqa: E402
    CRS,
    EE_IMAGE,
    MERIT_BANDS,
    MERIT_LAYERS,
    SCALE_M,
    MeritLayer,
    init_ee,
    load_merit_site,
    load_site_roi,
    reexec_with_repo_venv_if_needed,
    resolve_site_slugs,
)
from qa_merit import QA_BY_LAYER  # noqa: E402

DEFAULT_ORDER: tuple[MeritLayer, ...] = MERIT_LAYERS


@dataclass
class SiteRunResult:
    site: str
    display_name: str
    ok: bool
    error: str | None = None
    outputs: dict[str, str] = field(default_factory=dict)


def _export_band(
    merit: Any,
    roi: Any,
    *,
    band: MeritLayer,
    out_path: Path,
) -> Path:
    from gee_local_export import export_image_to_input  # noqa: E402

    img = (
        merit.select(MERIT_BANDS[band])
        .clip(roi)
        .reproject(crs=CRS, scale=SCALE_M)
        .toFloat()
    )
    export_image_to_input(
        img,
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
    layers: tuple[MeritLayer, ...] = DEFAULT_ORDER,
    authenticate: bool = False,
    write_qa: bool = True,
    qa_only: bool = False,
    dry_run: bool = False,
) -> SiteRunResult:
    cfg = load_merit_site(site)
    display = str(cfg.get("display_name") or site)
    paths = {layer: Path(cfg["merit_paths"][layer]) for layer in MERIT_LAYERS}
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

    merit = None
    roi = None
    if not qa_only:
        reexec_with_repo_venv_if_needed("numpy", "rasterio")
        ee = init_ee(authenticate=authenticate)
        roi = load_site_roi(cfg, ee)
        merit = ee.Image(EE_IMAGE)
        print(f"MERIT Hydro → {display} ({site}) · layers: {', '.join(layers)}")

    for layer in layers:
        out = paths[layer]
        if not qa_only:
            _export_band(merit, roi, band=layer, out_path=out)
        elif not out.is_file():
            raise FileNotFoundError(f"Missing GeoTIFF for --qa-only: {out}")
        outputs[layer] = str(out.resolve())
        print(f"{layer}: {out}")
        if write_qa:
            QA_BY_LAYER[layer](out, cfg, display=display)

    if write_qa and not dry_run:
        print(f"QA SVGs: {cfg['merit_qa_dir_abs']}")

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


def _parse_layers(raw: str | None) -> tuple[MeritLayer, ...]:
    if not raw:
        return DEFAULT_ORDER
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    valid = set(MERIT_LAYERS)
    unknown = [k for k in keys if k not in valid]
    if unknown:
        raise ValueError(f"Unknown layers: {unknown}. Valid: {', '.join(MERIT_LAYERS)}")
    return tuple(keys)  # type: ignore[return-value]


def _print_summary(results: list[SiteRunResult]) -> None:
    print("\n=== MERIT Hydro export summary ===")
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
        help=f"Comma-separated subset of: {','.join(MERIT_LAYERS)}",
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
    print(f"Layers: {', '.join(layers)}")

    results: list[SiteRunResult] = []
    for i, site in enumerate(sites, start=1):
        print(f"\n[{i}/{len(sites)}] {site}")
        try:
            results.append(
                run(
                    site,
                    layers=layers,
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
            f"--site {results[0].site} --hazard landslide"
        )
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
