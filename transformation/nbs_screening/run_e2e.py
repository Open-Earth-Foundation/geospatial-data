#!/usr/bin/env python3
"""End-to-end NBS site query exercise — flood, heat, or landslide screening.

Usage (from geospatial-data repo root):
    python transformation/nbs_screening/run_e2e.py
    python transformation/nbs_screening/run_e2e.py --hazard heat
    python transformation/nbs_screening/run_e2e.py --hazard landslide
    python transformation/nbs_screening/run_e2e.py --hazard landslide --site Glória

Outputs:
    transformation/nbs_screening/output/nbs_site_query_humaita.json
    transformation/nbs_screening/output/nbs_site_query_heat_cidade_baixa.json
    transformation/nbs_screening/output/nbs_site_query_landslide_gloria.json
    transformation/nbs_screening/output/site_<slug>.geojson
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd

from catalog_layers import barrio_context, query_layers
from nbs_rules import recommend_all

NBS_E2E_ROOT = Path(__file__).resolve().parent
OUT_DIR = NBS_E2E_ROOT / "output"

FLOOD_DEFAULT_SITE = "Humaitá"
HEAT_DEFAULT_SITE = "Cidade Baixa"
LANDSLIDE_DEFAULT_SITE = "Glória"

DEFAULT_SITES = {
    "flood": FLOOD_DEFAULT_SITE,
    "heat": HEAT_DEFAULT_SITE,
    "landslide": LANDSLIDE_DEFAULT_SITE,
}

GRID_LAYER_IDS = {"app_hev_250m", "app_heat_250m", "app_landslide_90m", "sample_grid_1km"}

EXERCISE_IDS = {
    "flood": "nbs_site_query_flood_e2e",
    "heat": "nbs_site_query_heat_e2e",
    "landslide": "nbs_site_query_landslide_e2e",
}


def _slug(name: str) -> str:
    ascii_name = (
        name.lower()
        .replace("á", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")


def _mechanism_dict(mechanism) -> dict:
    if hasattr(mechanism, "riverine"):
        return {
            "riverine": mechanism.riverine,
            "pluvial": mechanism.pluvial,
            "low_lying": mechanism.low_lying,
            "drainage_constrained_gap": mechanism.drainage_constrained,
            "rationale": mechanism.rationale,
        }
    if hasattr(mechanism, "steep_activatable_slope"):
        return {
            "steep_activatable_slope": mechanism.steep_activatable_slope,
            "rainfall_trigger": mechanism.rainfall_trigger,
            "low_cohesion_wet": mechanism.low_cohesion_wet,
            "vegetation_deficit": mechanism.vegetation_deficit,
            "drainage_saturation": mechanism.drainage_saturation,
            "disturbed_bare_slope": mechanism.disturbed_bare_slope,
            "upslope_convergence": mechanism.upslope_convergence,
            "high_social_exposure": mechanism.high_social_exposure,
            "rationale": mechanism.rationale,
        }
    return {
        "uhi_built_up": mechanism.uhi_built_up,
        "shade_deficit": mechanism.shade_deficit,
        "high_daytime_lst": mechanism.high_daytime_lst,
        "limited_nocturnal_cooling": mechanism.limited_nocturnal_cooling,
        "high_social_exposure": mechanism.high_social_exposure,
        "rationale": mechanism.rationale,
    }


def run(hazard: str, site_name: str) -> None:
    ctx_row = barrio_context(site_name, hazard=hazard)
    site_geom = ctx_row.pop("geometry")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slug(site_name)
    site_path = OUT_DIR / f"site_{slug}.geojson"
    gpd.GeoDataFrame([{"name": site_name, "geometry": site_geom}], crs="EPSG:4326").to_file(
        site_path, driver="GeoJSON"
    )

    layers = query_layers(site_geom, hazard=hazard)

    ctx: dict = {"bairro": site_name, "hazard": hazard, **ctx_row}
    grid_stats: dict = {}
    water_stats: dict = {}

    for layer in layers:
        if layer.layer_id in GRID_LAYER_IDS:
            grid_stats = layer.stats
        elif layer.layer_id == "osm_waterways":
            water_stats = {**layer.stats, "_note": layer.note}
        elif layer.status == "ok" and layer.layer_id in (
            "merit_hand",
            "merit_upa",
            "flood_hazard",
            "flood_risk",
            "heat_hazard",
            "heat_risk",
            "landslide_hazard",
            "landslide_risk",
            "ghsl_built_up",
            "hansen_treecover2000",
            "ndvi_p10_djf",
        ):
            ctx[f"{layer.layer_id}_mean"] = layer.stats.get("mean")

    mechanism, recommendations = recommend_all(ctx, grid_stats, water_stats, hazard=hazard)

    site_notes = {
        "flood": "High flood-risk bairro adjacent to Rio Gravataí — zone-level screening (CBO neighborhood flow).",
        "heat": "Dense central bairro — heat risk screening with LST / built-up / vegetation proxies.",
        "landslide": "Hillslope bairro — landslide susceptibility screening (slope ≥15° gate in hazard score).",
    }

    report = {
        "exercise": EXERCISE_IDS[hazard],
        "hazard": hazard,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site": {
            "name": site_name,
            "type": "bairro_polygon",
            "geojson": str(site_path),
            "note": site_notes[hazard],
        },
        "step_0_priority": ctx,
        "step_1_layers": [
            {
                "layer_id": l.layer_id,
                "source": l.source,
                "status": l.status,
                "stats": l.stats,
                "note": l.note,
            }
            for l in layers
        ],
        "step_1_mechanism": _mechanism_dict(mechanism),
        "step_2_nbs_recommendations": [asdict(r) for r in recommendations],
        "query_patterns": [
            "mask(catalog_cog, site_polygon) → zonal mean/median/p90",
            f"grid_metrics(site_polygon, hazard='{hazard}') → aggregated screening stats",
            "distance(site_polygon, osm_waterways) → nearest river / intersect",
            f"barrio join → OEF {hazard} risk output for Step 0",
        ],
        "gaps_discovered": _collect_gaps(layers, recommendations),
    }

    prefix = "nbs_site_query" if hazard == "flood" else f"nbs_site_query_{hazard}"
    out_path = OUT_DIR / f"{prefix}_{slug}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    _print_summary(report, out_path)


def _collect_gaps(layers, recommendations) -> list[str]:
    gaps: list[str] = []
    for layer in layers:
        if layer.status == "error":
            gaps.append(f"Catalog layer `{layer.layer_id}` not readable: {layer.note}")
    for rec in recommendations:
        gaps.extend(rec.gaps)
    return sorted(set(gaps))


def _print_summary(report: dict, out_path: Path) -> None:
    hazard = report["hazard"]
    print("=" * 60)
    print(f"NBS site query E2E ({hazard}) —", report["site"]["name"])
    print("=" * 60)
    ctx = report["step_0_priority"]
    print(f"Step 0  risk_mean = {ctx['risk_mean']:.3f}")
    if hazard in {"heat", "landslide"} and "hazard_mean" in ctx:
        print(f"        hazard_mean = {ctx['hazard_mean']:.3f}")
    mech = report["step_1_mechanism"]
    if hazard == "flood":
        print(
            f"Step 1  mechanism: riverine={mech['riverine']} pluvial={mech['pluvial']} "
            f"low_lying={mech['low_lying']}"
        )
    elif hazard == "landslide":
        print(
            f"Step 1  mechanism: steep_slope={mech['steep_activatable_slope']} "
            f"veg_deficit={mech['vegetation_deficit']} drainage={mech['drainage_saturation']}"
        )
    else:
        print(
            f"Step 1  mechanism: uhi={mech['uhi_built_up']} shade_deficit={mech['shade_deficit']} "
            f"high_daytime_lst={mech['high_daytime_lst']}"
        )
    print("\nStep 2  NBS screening (top 5):")
    for rec in report["step_2_nbs_recommendations"][:5]:
        print(f"  {rec['score']:.2f}  {rec['nbs_type']}")
        print(f"         {rec['rationale'][:100]}...")
    print(f"\nGaps: {len(report['gaps_discovered'])} listed in report")
    print(f"Written: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="NBS site query E2E (flood, heat, or landslide)")
    parser.add_argument(
        "--hazard",
        choices=("flood", "heat", "landslide"),
        default="flood",
        help="Climate hazard profile (default: flood)",
    )
    parser.add_argument(
        "--site",
        default=None,
        help="Bairro name (default depends on hazard)",
    )
    args = parser.parse_args()
    site_name = args.site or DEFAULT_SITES[args.hazard]
    run(args.hazard, site_name)


if __name__ == "__main__":
    main()
