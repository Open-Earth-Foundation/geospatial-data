#!/usr/bin/env python3
"""Compute grid-cell heat mechanism type for a city (NBS screening H2).

Screens each hazard-valid 250 m cell inside the city boundary, classifies the
dominant heat mechanism, IDW-fills gaps, and writes GeoTIFF + GeoJSON exports.

Example:
  python transformation/nbs_screening/heat/compute_mechanism.py --site richfield
  python transformation/nbs_screening/heat/compute_mechanism.py --site porto_alegre --aoi full
  python transformation/nbs_screening/check_nbs_layers.py --site richfield --hazard heat
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

HEAT_ROOT = Path(__file__).resolve().parent
NBS_ROOT = HEAT_ROOT.parent
for _path in (HEAT_ROOT, NBS_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from catalog_layers import (  # noqa: E402
    HAZARD_REQUIRED_LAYERS,
    get_layer_sources,
    get_reference_hazard_raster,
)
from grid_screening import (  # noqa: E402
    MECHANISM_RASTER_NODATA,
    export_heat_mechanism_layers,
    heat_mechanism_layer_stem,
    result_to_geojson,
    result_to_report_dict,
    screen_site_heat_mechanism_grid,
    site_reference_bounds_geom,
)
from nbs_rules import (  # noqa: E402
    HEAT_MECHANISM_COLORS,
    HEAT_MECHANISM_DISPLAY_LABELS,
    HEAT_MECHANISM_TYPE_CODES,
)
from site_config import (  # noqa: E402
    DEFAULT_SITE,
    SITE_ENV_VAR,
    find_repo_root,
    load_site_config,
    site_output_dir,
)

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    import rasterio
except ImportError:  # pragma: no cover
    rasterio = None


HEAT_MECHANISM_CLASS_NAMES: dict[int, str] = {
    code: HEAT_MECHANISM_DISPLAY_LABELS[mech_type]
    for mech_type, code in HEAT_MECHANISM_TYPE_CODES.items()
}
HEAT_MECHANISM_CODE_COLORS: dict[int, str] = {
    code: HEAT_MECHANISM_COLORS[mech_type]
    for mech_type, code in HEAT_MECHANISM_TYPE_CODES.items()
}
NODATA_FILL = "#eeeeee"


def write_heat_mechanism_grid_svg(
    raster_path: Path,
    out_path: Path,
    *,
    title: str,
    subtitle: str = "",
    width: int = 900,
    height: int = 780,
) -> Path:
    if rasterio is None:
        raise ImportError("rasterio required for QA map generation")

    with rasterio.open(raster_path) as ds:
        arr = ds.read(1)

    a = np.asarray(arr, dtype=np.uint8)
    nrows, ncols = a.shape
    legend_w = 240
    margin_l, margin_t, margin_b = 20, 70, 20
    map_w = width - legend_w - 40
    map_h = height - margin_t - margin_b
    cell_w = map_w / ncols
    cell_h = map_h / nrows

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#fafafa"/>',
        f'<text x="20" y="32" font-family="Helvetica, Arial, sans-serif" font-size="18" font-weight="bold">{title}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="20" y="52" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#444">{subtitle}</text>'
        )

    for i in range(nrows):
        for j in range(ncols):
            code = int(a[i, j])
            fill = NODATA_FILL if code == MECHANISM_RASTER_NODATA else HEAT_MECHANISM_CODE_COLORS.get(code, "#cccccc")
            x = margin_l + j * cell_w
            y = margin_t + i * cell_h
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w:.2f}" height="{cell_h:.2f}" '
                f'fill="{fill}" stroke="none"/>'
            )

    parts.append(
        f'<rect x="{margin_l}" y="{margin_t}" width="{map_w}" height="{map_h}" '
        f'fill="none" stroke="#666" stroke-width="1"/>'
    )

    lx = width - legend_w
    parts.append(
        f'<text x="{lx}" y="90" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="11" font-weight="bold">Mechanism code</text>'
    )
    legend_rows = [
        (MECHANISM_RASTER_NODATA, NODATA_FILL, "No data"),
        *[
            (code, HEAT_MECHANISM_CODE_COLORS[code], f"{code} · {HEAT_MECHANISM_CLASS_NAMES[code]}")
            for code in sorted(HEAT_MECHANISM_CODE_COLORS)
        ],
    ]
    for idx, (_code, color, label) in enumerate(legend_rows):
        y = 108 + idx * 22
        parts.append(f'<rect x="{lx}" y="{y}" width="18" height="18" fill="{color}" stroke="#666"/>')
        parts.append(
            f'<text x="{lx + 26}" y="{y + 14}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="10">{label}</text>'
        )

    parts.append("</svg>")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote map: {out_path}")
    return out_path


def model_config_path() -> Path:
    return find_repo_root(NBS_ROOT) / "models" / "nbs_heat_mechanism_type" / "config.yaml"


def load_model_config() -> dict[str, Any]:
    path = model_config_path()
    if not path.is_file():
        return {}
    if yaml is None:
        raise ImportError("PyYAML required to load model config")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _require_layers(site: str) -> None:
    sources = get_layer_sources("heat", site)
    missing = [layer for layer in HAZARD_REQUIRED_LAYERS["heat"] if layer not in sources]
    if missing:
        raise FileNotFoundError(
            f"Missing required heat layers for site={site}: {missing}. "
            f"Run: python transformation/nbs_screening/check_nbs_layers.py --site {site} --hazard heat"
        )


def _resolve_aoi(site: str, aoi_mode: str):
    if aoi_mode == "full":
        return site_reference_bounds_geom("heat", site)
    if aoi_mode == "boundary":
        return None
    raise ValueError(f"Unknown --aoi mode: {aoi_mode}")


def compute_heat_mechanism(
    site: str,
    *,
    aoi: str = "boundary",
    include_nbs: bool = False,
    out_dir: Path | None = None,
    write_qa: bool = True,
) -> dict[str, Any]:
    site_cfg = load_site_config(site)
    model_cfg = load_model_config()

    _require_layers(site)
    ref_path = get_reference_hazard_raster("heat", site)
    out_dir = Path(out_dir or site_output_dir(site, "heat"))
    out_dir.mkdir(parents=True, exist_ok=True)

    aoi_geom = _resolve_aoi(site, aoi)
    print(f"Screening heat mechanism grid for {site_cfg.get('display_name', site)} ({site})")
    print(f"  reference hazard: {ref_path}")
    print(f"  AOI mode: {aoi}")
    print(f"  output: {out_dir}")

    result = screen_site_heat_mechanism_grid(
        site,
        aoi_geom=aoi_geom,
        include_nbs=include_nbs,
        sample_catalog=True,
    )

    raster_paths = export_heat_mechanism_layers(result, out_dir, site=site)
    stem = heat_mechanism_layer_stem(site)
    geojson_path = out_dir / f"{stem}.geojson"
    report_path = out_dir / f"nbs_grid_heat_{site}.json"

    geojson_payload = result_to_geojson(result)
    geojson_payload["properties"]["layer"] = (
        "poa_heat_mechanism_type" if site == DEFAULT_SITE else f"{site}_heat_mechanism_type"
    )
    geojson_payload["properties"]["site"] = site
    geojson_path.write_text(json.dumps(geojson_payload, indent=2), encoding="utf-8")

    report = result_to_report_dict(result)
    report["site"] = site
    report["outputs"] = {key: str(path) for key, path in raster_paths.items()}
    report["geojson"] = str(geojson_path)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    display = str(site_cfg.get("display_name") or site)
    qa_map_path: Path | None = None
    if write_qa:
        filled_path = raster_paths["filled"]
        qa_map_path = out_dir / f"map_{filled_path.stem}.svg"
        write_heat_mechanism_grid_svg(
            filled_path,
            qa_map_path,
            title=f"Heat mechanism type (IDW-filled) — {display}",
            subtitle=f"250 m grid · {filled_path.name}",
        )

    meta = {
        "site_slug": site,
        "display_name": site_cfg.get("display_name"),
        "hazard": "heat",
        "layer_id": model_cfg.get("layer_id", "nbs_heat_mechanism_type"),
        "model_version": model_cfg.get("version", "v1"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "aoi_mode": aoi,
        "reference_hazard_raster": str(ref_path),
        "mechanism_summary": result.mechanism_summary,
        "outputs": {
            **{k: str(v) for k, v in raster_paths.items()},
            "geojson": str(geojson_path),
            "report_json": str(report_path),
            **({"qa_map": str(qa_map_path)} if qa_map_path else {}),
        },
    }
    meta_path = out_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Wrote {meta_path}")
    print(f"Wrote {geojson_path}")
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help=f"City slug (default: {DEFAULT_SITE} or {SITE_ENV_VAR})")
    parser.add_argument(
        "--aoi",
        choices=("boundary", "full"),
        default="boundary",
        help="AOI for screening: city boundary GeoJSON or full hazard grid extent",
    )
    parser.add_argument(
        "--include-nbs",
        action="store_true",
        help="Also score NbS recommendations per cell (slower)",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Override output directory (default: heat/sites/<site>/data/output)",
    )
    parser.add_argument(
        "--no-qa",
        action="store_true",
        help="Skip QA SVG map for the filled mechanism raster",
    )
    args = parser.parse_args(argv)

    site = args.site or os.environ.get(SITE_ENV_VAR, DEFAULT_SITE)
    try:
        compute_heat_mechanism(
            site,
            aoi=args.aoi,
            include_nbs=args.include_nbs,
            out_dir=Path(args.out_dir) if args.out_dir else None,
            write_qa=not args.no_qa,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
