"""Fetch flood layers once for a regional union bbox (GEE → cache/regions/.../layers/).

Pilot layers only (no city-domain reducers): GFPLAIN, JRC RP100, Aqueduct RP100.
City AOIs are filled later via ``clip_to_site.materialize_city_flood_inputs``.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .resolve import repo_root

# Sources safe for regional fetch (fixed transforms / physical units).
REGIONAL_FLOOD_SOURCES = ("gfplain", "jrc", "aqueduct")


@dataclass(frozen=True)
class RegionalLayerSpec:
    source: str  # gfplain | jrc | aqueduct
    stem: str  # filename without .tif
    scale_m: float
    band_role: str  # depth | norm | mask


LAYER_SPECS: tuple[RegionalLayerSpec, ...] = (
    RegionalLayerSpec("gfplain", "gfplain_250m", 250, "mask"),
    RegionalLayerSpec("jrc", "jrc_rp100_depth", 90, "depth"),
    RegionalLayerSpec("jrc", "jrc_rp100_depth_norm", 90, "norm"),
    RegionalLayerSpec("aqueduct", "aqueduct_depth_rp100", 1000, "depth"),
    RegionalLayerSpec("aqueduct", "aqueduct_depth_rp100_norm", 1000, "norm"),
)


def layers_dir(cache_dir: Path) -> Path:
    return Path(cache_dir) / "layers"


def load_union_bbox(cache_dir: Path) -> dict[str, float]:
    path = Path(cache_dir) / "union_bbox.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing union bbox: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: float(data[k]) for k in ("west", "south", "east", "north")}


def _init_flood_ee(*, authenticate: bool = False) -> Any:
    flood_root = repo_root() / "transformation" / "flood_hazard"
    if str(flood_root) not in sys.path:
        sys.path.insert(0, str(flood_root))
    from input_common import init_ee

    return init_ee(authenticate=authenticate)


def _export(image: Any, *, filename: str, region: Any, scale: float, out_dir: Path) -> Path:
    trans = repo_root() / "transformation"
    if str(trans) not in sys.path:
        sys.path.insert(0, str(trans))
    from gee_local_export import export_image_to_input

    return Path(
        export_image_to_input(
            image,
            filename=filename,
            region=region,
            scale=scale,
            input_dir=out_dir,
            crs="EPSG:4326",
            description=Path(filename).stem[:100],
            drive_folder="OEF_CCRA_Regional",
        )
    )


def _build_images(ee: Any, roi: Any, sources: set[str]) -> list[tuple[RegionalLayerSpec, Any]]:
    flood_root = repo_root() / "transformation" / "flood_hazard"
    if str(flood_root) not in sys.path:
        sys.path.insert(0, str(flood_root))
    from input_common import depth_to_impact_score

    built: list[tuple[RegionalLayerSpec, Any]] = []
    specs = [s for s in LAYER_SPECS if s.source in sources]

    if "gfplain" in sources:
        gfplain = ee.Image("IAHS/GFPLAIN250/v0").clip(roi)
        mask = ee.Image.constant(1).updateMask(gfplain.mask()).rename("gfplain_1")
        built.append((next(s for s in specs if s.stem == "gfplain_250m"), mask))

    if "jrc" in sources:
        image = ee.ImageCollection("JRC/CEMS_GLOFAS/FloodHazard/v2_1").mosaic()
        depth = image.select("RP100_depth").clip(roi).rename("depth_rp100_m").toFloat()
        score = depth_to_impact_score(depth, ee, band_name="hazard_score_rp100").clip(roi).toFloat()
        built.append((next(s for s in specs if s.stem == "jrc_rp100_depth"), depth))
        built.append((next(s for s in specs if s.stem == "jrc_rp100_depth_norm"), score))

    if "aqueduct" in sources:
        dataset = ee.ImageCollection("WRI/Aqueduct_Flood_Hazard_Maps/V2")
        river = (
            dataset.filter(ee.Filter.eq("floodtype", "inunriver"))
            .filter(ee.Filter.eq("returnperiod", 100))
            .filter(ee.Filter.eq("climatescenario", "historical"))
        )
        image = ee.Image(river.first()).clip(roi)
        depth = image.select("inundation_depth")
        score = depth_to_impact_score(depth, ee, band_name="flood_hazard_score").clip(roi)
        built.append((next(s for s in specs if s.stem == "aqueduct_depth_rp100"), depth))
        built.append((next(s for s in specs if s.stem == "aqueduct_depth_rp100_norm"), score))

    return built


def fetch_regional_flood_layers(
    cache_dir: Path,
    *,
    sources: Iterable[str] = REGIONAL_FLOOD_SOURCES,
    authenticate: bool = False,
    skip_existing: bool = True,
) -> dict[str, Path]:
    """Export regional flood layers into ``cache_dir/layers/``.

    Returns mapping ``stem → path`` for layers present after the call.
    """
    cache_dir = Path(cache_dir)
    out_dir = layers_dir(cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = {s.strip().lower() for s in sources if s.strip()}
    unknown = wanted - set(REGIONAL_FLOOD_SOURCES)
    if unknown:
        raise ValueError(f"Unsupported regional sources: {sorted(unknown)}")

    bbox = load_union_bbox(cache_dir)
    results: dict[str, Path] = {}
    pending_sources: set[str] = set()
    for spec in LAYER_SPECS:
        if spec.source not in wanted:
            continue
        path = out_dir / f"{spec.stem}.tif"
        if skip_existing and path.is_file():
            results[spec.stem] = path
            print(f"[regional-fetch] skip existing {path.name}")
        else:
            pending_sources.add(spec.source)

    if not pending_sources:
        _write_layers_manifest(cache_dir, results)
        return results

    ee = _init_flood_ee(authenticate=authenticate)
    roi = ee.Geometry.Rectangle(
        [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
    )
    print(
        f"[regional-fetch] union_bbox={bbox} sources={sorted(pending_sources)} → {out_dir}"
    )
    for spec, image in _build_images(ee, roi, pending_sources):
        path = _export(
            image,
            filename=f"{spec.stem}.tif",
            region=roi,
            scale=spec.scale_m,
            out_dir=out_dir,
        )
        results[spec.stem] = Path(path)

    # Re-scan directory for completeness
    for spec in LAYER_SPECS:
        if spec.source in wanted:
            path = out_dir / f"{spec.stem}.tif"
            if path.is_file():
                results[spec.stem] = path

    _write_layers_manifest(cache_dir, results)
    return results


def _write_layers_manifest(cache_dir: Path, results: dict[str, Path]) -> None:
    payload = {
        "note": (
            "Regional flood layers for multi-city clip. Fixed-transform sources only "
            "(GFPLAIN / JRC / Aqueduct). GFD and heat norms stay per-city."
        ),
        "layers": {stem: str(path) for stem, path in sorted(results.items())},
    }
    (Path(cache_dir) / "layers_manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def available_regional_sources(cache_dir: Path) -> set[str]:
    """Return source keys that have all expected stems on disk."""
    out_dir = layers_dir(cache_dir)
    present: set[str] = set()
    for source in REGIONAL_FLOOD_SOURCES:
        stems = [s.stem for s in LAYER_SPECS if s.source == source]
        if stems and all((out_dir / f"{stem}.tif").is_file() for stem in stems):
            present.add(source)
    return present


def materialize_sites_from_regional(
    cache_dir: Path,
    site_slugs: Iterable[str],
) -> dict[str, dict[str, Path]]:
    """Clip regional layers into each city's flood_hazard data/input."""
    flood_root = repo_root() / "transformation" / "flood_hazard"
    if str(flood_root) not in sys.path:
        sys.path.insert(0, str(flood_root))
    from input_common import load_flood_site

    from .clip_to_site import materialize_city_flood_inputs

    out: dict[str, dict[str, Path]] = {}
    layers = layers_dir(cache_dir)
    for slug in site_slugs:
        cfg = load_flood_site(slug)
        written = materialize_city_flood_inputs(layers, cfg)
        out[slug] = written
        print(f"[regional-clip] {slug}: {len(written)} layer(s)")
    return out
