#!/usr/bin/env python3
"""Compute grid-cell flood mechanism type for a city (NBS screening N2).

Screens each hazard-valid 250 m cell inside the city boundary, classifies the
dominant flood mechanism, IDW-fills gaps, and writes GeoTIFF + GeoJSON exports.

Example:
  python transformation/nbs_screening/compute_nbs_mechanism.py --site richfield
  python transformation/nbs_screening/compute_nbs_mechanism.py --site porto_alegre --aoi full
  python transformation/nbs_screening/check_nbs_layers.py --site richfield --hazard flood
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NBS_ROOT = Path(__file__).resolve().parent
if str(NBS_ROOT) not in sys.path:
    sys.path.insert(0, str(NBS_ROOT))

from catalog_layers import (  # noqa: E402
    HAZARD_REQUIRED_LAYERS,
    get_layer_sources,
    get_reference_hazard_raster,
)
from grid_screening import (  # noqa: E402
    export_flood_mechanism_layers,
    flood_mechanism_layer_stem,
    result_to_geojson,
    result_to_report_dict,
    screen_site_flood_mechanism_grid,
    site_reference_bounds_geom,
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


def model_config_path() -> Path:
    return find_repo_root(NBS_ROOT) / "models" / "nbs_flood_mechanism_type" / "config.yaml"


def load_model_config() -> dict[str, Any]:
    path = model_config_path()
    if not path.is_file():
        return {}
    if yaml is None:
        raise ImportError("PyYAML required to load model config")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _require_layers(site: str, hazard: str = "flood") -> None:
    sources = get_layer_sources(hazard, site)  # type: ignore[arg-type]
    missing = [layer for layer in HAZARD_REQUIRED_LAYERS[hazard] if layer not in sources]  # type: ignore[index]
    if missing:
        raise FileNotFoundError(
            f"Missing required {hazard} layers for site={site}: {missing}. "
            f"Run: python transformation/nbs_screening/check_nbs_layers.py --site {site} --hazard {hazard}"
        )


def _resolve_aoi(site: str, aoi_mode: str):
    if aoi_mode == "full":
        return site_reference_bounds_geom("flood", site)
    if aoi_mode == "boundary":
        return None  # screen_site_flood_mechanism_grid loads boundary
    raise ValueError(f"Unknown --aoi mode: {aoi_mode}")


def compute_flood_mechanism(
    site: str,
    *,
    aoi: str = "boundary",
    include_nbs: bool = False,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    site_cfg = load_site_config(site)
    model_cfg = load_model_config()

    _require_layers(site, "flood")
    ref_path = get_reference_hazard_raster("flood", site)
    out_dir = Path(out_dir or site_output_dir(site))
    out_dir.mkdir(parents=True, exist_ok=True)

    aoi_geom = _resolve_aoi(site, aoi)
    print(f"Screening flood mechanism grid for {site_cfg.get('display_name', site)} ({site})")
    print(f"  reference hazard: {ref_path}")
    print(f"  AOI mode: {aoi}")
    print(f"  output: {out_dir}")

    result = screen_site_flood_mechanism_grid(
        site,
        aoi_geom=aoi_geom,
        include_nbs=include_nbs,
        sample_catalog=True,
    )

    raster_paths = export_flood_mechanism_layers(result, out_dir, site=site)
    stem = flood_mechanism_layer_stem(site)
    geojson_path = out_dir / f"{stem}.geojson"
    report_path = out_dir / f"nbs_grid_flood_{site}.json"

    geojson_payload = result_to_geojson(result)
    geojson_payload["properties"]["layer"] = (
        "poa_flood_mechanism_type" if site == DEFAULT_SITE else f"{site}_flood_mechanism_type"
    )
    geojson_payload["properties"]["site"] = site
    geojson_path.write_text(json.dumps(geojson_payload, indent=2), encoding="utf-8")

    report = result_to_report_dict(result)
    report["site"] = site
    report["outputs"] = {key: str(path) for key, path in raster_paths.items()}
    report["geojson"] = str(geojson_path)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    meta = {
        "site_slug": site,
        "display_name": site_cfg.get("display_name"),
        "hazard": "flood",
        "layer_id": model_cfg.get("layer_id", "nbs_flood_mechanism_type"),
        "model_version": model_cfg.get("version", "v1"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "aoi_mode": aoi,
        "reference_hazard_raster": str(ref_path),
        "mechanism_summary": result.mechanism_summary,
        "outputs": {
            **{k: str(v) for k, v in raster_paths.items()},
            "geojson": str(geojson_path),
            "report_json": str(report_path),
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
        "--hazard",
        choices=("flood",),
        default="flood",
        help="Hazard profile (N2: flood only)",
    )
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
        help="Override output directory (default: nbs_screening/sites/<site>/data/output)",
    )
    args = parser.parse_args(argv)

    site = args.site or os.environ.get(SITE_ENV_VAR, DEFAULT_SITE)
    if args.hazard != "flood":
        print("ERROR: N2 supports --hazard flood only", file=sys.stderr)
        return 1

    try:
        compute_flood_mechanism(
            site,
            aoi=args.aoi,
            include_nbs=args.include_nbs,
            out_dir=Path(args.out_dir) if args.out_dir else None,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
