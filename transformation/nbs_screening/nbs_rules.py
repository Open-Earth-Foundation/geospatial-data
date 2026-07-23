"""Screening rules for flood and heat NBS — maps layer stats → mechanism → candidate NBS types.

Rules mirror `docs/recommended-datasets.md` (Steps 1–2) and hazard lens documents.
Scores are exploratory (0–1), not engineering suitability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

HazardKind = Literal["flood", "heat", "landslide"]

# Shared symbology: mixed = multiple competing mechanisms (screening concern, not neutral).
MECHANISM_MIXED_COLOR = "#8e0152"

FloodMechanismType = Literal[
    "riverine", "pluvial", "low_lying", "drainage_constrained", "mixed", "none"
]

# Integer codes for catalog raster / GeoJSON (ON-5990)
FLOOD_MECHANISM_TYPE_CODES: dict[FloodMechanismType, int] = {
    "none": 0,
    "riverine": 1,
    "pluvial": 2,
    "low_lying": 3,
    "drainage_constrained": 4,
    "mixed": 5,
}
FLOOD_MECHANISM_CODE_TO_TYPE: dict[int, FloodMechanismType] = {
    v: k for k, v in FLOOD_MECHANISM_TYPE_CODES.items()
}

FLOOD_MECHANISM_CATALOG_DOCS = """
| Code | Type | Meaning | Primary proxies |
|------|------|---------|-----------------|
| 0 | none | No mechanism above screening threshold | — |
| 1 | riverine | Fluvial / channel proximity | OSM waterway distance < 500 m or intersects |
| 2 | pluvial | Urban runoff / intense rainfall on impervious surfaces | GHSL/Dynamic World built-up; CHIRPS heavy rain |
| 3 | low_lying | Depression / floodplain / wetness accumulation | GFPLAIN, depression mask, HAND ≤ 5 m, JRC surface water |
| 4 | drainage_constrained | Urban drainage bottleneck (proxy) | High built-up + low HAND + pluvial signal, not riverine |
| 5 | mixed | Two+ mechanisms within strength tie band | Multiple flags within 0.15 of top score |

Note: `drainage_constrained` is a **proxy** until municipal storm-drain data exists.
Application-layer NBS filters (e.g. wetland only near wetlands) stay outside this catalog layer.
""".strip()

HeatMechanismType = Literal[
    "without_clear_dominant",
    "uhi_built_up",
    "shade_deficit",
    "high_daytime_lst",
    "limited_nocturnal_cooling",
    "high_social_exposure",
    "mixed",
]

# Dominant-type threshold for heat grid screening (lower than flood default 0.2).
HEAT_MIN_STRENGTH = 0.15

HEAT_MECHANISM_TYPE_CODES: dict[HeatMechanismType, int] = {
    "without_clear_dominant": 0,
    "uhi_built_up": 1,
    "shade_deficit": 2,
    "high_daytime_lst": 3,
    "limited_nocturnal_cooling": 4,
    "high_social_exposure": 5,
    "mixed": 6,
}
HEAT_MECHANISM_CODE_TO_TYPE: dict[int, HeatMechanismType] = {
    v: k for k, v in HEAT_MECHANISM_TYPE_CODES.items()
}

HEAT_MECHANISM_DISPLAY_LABELS: dict[HeatMechanismType, str] = {
    "without_clear_dominant": "without a clear dominant mechanism",
    "uhi_built_up": "uhi_built_up",
    "shade_deficit": "shade_deficit",
    "high_daytime_lst": "high_daytime_lst",
    "limited_nocturnal_cooling": "limited_nocturnal_cooling",
    "high_social_exposure": "high_social_exposure",
    "mixed": "mixed",
}

HEAT_MECHANISM_CATALOG_DOCS = """
| Code | Type | Meaning | Primary proxies |
|------|------|---------|-----------------|
| 0 | without_clear_dominant | Without a clear dominant mechanism (all strengths < 0.15) | Weak or marginal screening signals |
| 1 | uhi_built_up | Urban heat island / built-up low vegetation | GHSL/DW built-up ≥ 0.35 with low vegetation proxy |
| 2 | shade_deficit | Lack of canopy / tree cover | Low tree %, Hansen tree cover < 20%, low green in built areas |
| 3 | high_daytime_lst | High daytime surface heating | Heat hazard ≥ 0.45 or Landsat/MODIS day LST norm ≥ 0.55 |
| 4 | limited_nocturnal_cooling | Nighttime heat retention | MODIS night ≥ day + 0.05 with night LST ≥ 0.5 |
| 5 | high_social_exposure | High heat risk / exposure / vulnerability | Risk ≥ 0.35 or E/V ≥ 0.5 |
| 6 | mixed | Two+ mechanisms within strength tie band | Multiple strengths within 0.15 of top score |

Note: LST proxies measure **surface** temperature, not pedestrian thermal comfort.
Application-layer NBS filters stay outside this catalog layer.
""".strip()

LandslideMechanismType = Literal[
    "without_clear_dominant",
    "steep_activatable_slope",
    "rainfall_trigger",
    "low_cohesion_wet",
    "vegetation_deficit",
    "drainage_saturation",
    "disturbed_bare_slope",
    "upslope_convergence",
    "high_social_exposure",
    "mixed",
]

LANDSLIDE_MIN_STRENGTH = 0.15

LANDSLIDE_MECHANISM_TYPE_CODES: dict[LandslideMechanismType, int] = {
    "without_clear_dominant": 0,
    "steep_activatable_slope": 1,
    "rainfall_trigger": 2,
    "low_cohesion_wet": 3,
    "vegetation_deficit": 4,
    "drainage_saturation": 5,
    "disturbed_bare_slope": 6,
    "upslope_convergence": 7,
    "high_social_exposure": 8,
    "mixed": 9,
}
LANDSLIDE_MECHANISM_CODE_TO_TYPE: dict[int, LandslideMechanismType] = {
    v: k for k, v in LANDSLIDE_MECHANISM_TYPE_CODES.items()
}

LANDSLIDE_MECHANISM_DISPLAY_LABELS: dict[LandslideMechanismType, str] = {
    "without_clear_dominant": "without a clear dominant mechanism",
    "steep_activatable_slope": "steep_activatable_slope",
    "rainfall_trigger": "rainfall_trigger",
    "low_cohesion_wet": "low_cohesion_wet",
    "vegetation_deficit": "vegetation_deficit",
    "drainage_saturation": "drainage_saturation",
    "disturbed_bare_slope": "disturbed_bare_slope",
    "upslope_convergence": "upslope_convergence",
    "high_social_exposure": "high_social_exposure",
    "mixed": "mixed",
}

LANDSLIDE_MECHANISM_CATALOG_DOCS = """
| Code | Type | Meaning | Primary proxies |
|------|------|---------|-----------------|
| 0 | without_clear_dominant | Without a clear dominant mechanism (all strengths < 0.15) | Weak or marginal screening signals |
| 1 | steep_activatable_slope | Slope activation gate / susceptibility | Slope ≥ 15° or landslide hazard > 0 |
| 2 | rainfall_trigger | Chronic extreme rainfall | CHIRPS R90p climatology ≥ 200 mm |
| 3 | low_cohesion_wet | Low cohesion when wet | SoilGrids clay ≥ 35% |
| 4 | vegetation_deficit | Lack of stabilizing cover | Low NDVI P10, tree, or green cover |
| 5 | drainage_saturation | Drainage convergence / saturation | HAND ≤ 5 m or near waterways |
| 6 | disturbed_bare_slope | Disturbed or bare slope | Dynamic World bare/built fractions |
| 7 | upslope_convergence | Upslope contributing area | MERIT UPA ≥ 1 km² |
| 8 | high_social_exposure | High landslide risk / E / V | Risk ≥ 0.03 or elevated E/V |
| 9 | mixed | Two+ mechanisms within strength tie band | Multiple strengths within 0.15 of top score |

Note: Landslide hazard is a **screening susceptibility index**, not failure probability.
Application-layer NBS filters stay outside this catalog layer.
""".strip()


@dataclass
class MechanismAssessment:
    riverine: bool
    pluvial: bool
    low_lying: bool
    drainage_constrained: bool
    rationale: list[str] = field(default_factory=list)


@dataclass
class FloodMechanismClassification:
    """Dominant grid-level flood mechanism (ON-5990 catalog layer)."""

    mechanism_type: FloodMechanismType
    mechanism_code: int
    strengths: dict[str, float]
    rationale: list[str] = field(default_factory=list)


@dataclass
class HeatMechanismClassification:
    """Dominant grid-level heat mechanism (ON-5991 catalog layer)."""

    mechanism_type: HeatMechanismType
    mechanism_code: int
    strengths: dict[str, float]
    rationale: list[str] = field(default_factory=list)


@dataclass
class LandslideMechanismClassification:
    """Dominant grid-level landslide mechanism (POA 90 m catalog layer)."""

    mechanism_type: LandslideMechanismType
    mechanism_code: int
    strengths: dict[str, float]
    rationale: list[str] = field(default_factory=list)


@dataclass
class HeatMechanismAssessment:
    uhi_built_up: bool
    shade_deficit: bool
    high_daytime_lst: bool
    limited_nocturnal_cooling: bool
    high_social_exposure: bool
    rationale: list[str] = field(default_factory=list)


@dataclass
class NbsRecommendation:
    nbs_type: str
    score: float
    rationale: str
    gaps: list[str] = field(default_factory=list)


def _get(stats: dict[str, Any], key: str, default: float | None = None) -> float | None:
    val = stats.get(key)
    if val is None:
        return default
    return float(val)


def _normalize_lst_signal(val: float | None) -> float | None:
    """Map catalog LST (°C P90 composites or 0–1 norm) to a 0–1 screening scale."""
    if val is None:
        return None
    if val <= 1.5:
        return float(val)
    # POA DJF / P90 surface-temperature approximate range for screening (°C).
    return min(1.0, max(0.0, (float(val) - 20.0) / 25.0))


def _heavy_rain_signal(grid: dict[str, Any]) -> bool:
    """Screening-only CHIRPS signal; local IDF is still needed for sizing."""
    rx1day = _get(grid, "rx1day_2024_mean")
    rx5day = _get(grid, "rx5day_2024_mean")
    return bool((rx1day is not None and rx1day >= 50) or (rx5day is not None and rx5day >= 100))


def infer_flood_mechanism(
    ctx: dict[str, Any], grid: dict[str, Any], water: dict[str, Any]
) -> MechanismAssessment:
    """Step 1 — flood mechanism from diagnostic proxies."""
    rationale: list[str] = []
    dist_river = _get(water, "dist_nearest_m", 9999)
    intersects = water.get("intersects_waterway", 0)
    imperv = _get(grid, "imperv_pct_mean")
    dw_built = _get(grid, "dw_built_pct_mean")
    floodplain = _get(grid, "floodplain_adj_pct_mean")
    depression = _get(grid, "depression_pct_mean")
    water_occurrence = _get(grid, "surface_water_occurrence_mean")
    water_seasonality = _get(grid, "surface_water_seasonality_mean")
    heavy_rain = _heavy_rain_signal(grid)
    hand = _get(ctx, "merit_hand_mean") or _get(grid, "merit_hand_mean")

    riverine = bool(intersects or (dist_river is not None and dist_river < 500))
    if riverine:
        rationale.append(f"Riverine signal: waterway within ~{dist_river:.0f} m or intersects.")

    runoff_proxy = max(v for v in [imperv, dw_built, 0.0] if v is not None)
    pluvial = bool(runoff_proxy >= 0.35 or (runoff_proxy >= 0.25 and heavy_rain))
    if pluvial:
        rationale.append(
            f"Pluvial signal: runoff proxy {runoff_proxy:.2f}; "
            f"CHIRPS heavy-rain signal={heavy_rain}."
        )

    low_lying = bool(
        (floodplain is not None and floodplain >= 0.5)
        or (depression is not None and depression >= 0.15)
        or (hand is not None and hand <= 5)
        or (water_occurrence is not None and water_occurrence >= 10)
        or (water_seasonality is not None and water_seasonality >= 1)
    )
    if low_lying:
        rationale.append(
            "Low-lying/wetness signal: "
            f"floodplain_adj={floodplain}, depression_pct={depression}, HAND={hand}, "
            f"JRC occurrence={water_occurrence}, seasonality={water_seasonality}."
        )

    rationale.append("Drainage-constrained: no open urban drainage layer — gap.")

    return MechanismAssessment(
        riverine=riverine,
        pluvial=pluvial,
        low_lying=low_lying,
        drainage_constrained=True,
        rationale=rationale,
    )


def flood_mechanism_strengths(
    ctx: dict[str, Any], grid: dict[str, Any], water: dict[str, Any]
) -> dict[str, float]:
    """Continuous 0–1 strength per mechanism type for grid-level classification."""
    dist_river = _get(water, "dist_nearest_m", 9999) or 9999
    intersects = bool(water.get("intersects_waterway", 0))
    imperv = _get(grid, "imperv_pct_mean")
    dw_built = _get(grid, "dw_built_pct_mean")
    floodplain = _get(grid, "floodplain_adj_pct_mean")
    depression = _get(grid, "depression_pct_mean")
    water_occurrence = _get(grid, "surface_water_occurrence_mean")
    water_seasonality = _get(grid, "surface_water_seasonality_mean")
    heavy_rain = _heavy_rain_signal(grid)
    hand = _get(ctx, "merit_hand_mean") or _get(grid, "merit_hand_mean")

    runoff_proxy = max(v for v in [imperv, dw_built, 0.0] if v is not None)

    if intersects:
        riverine = 1.0
    elif dist_river < 500:
        riverine = max(0.0, 1.0 - dist_river / 500.0)
    else:
        riverine = 0.0

    pluvial = 0.0
    if runoff_proxy >= 0.35:
        pluvial = min(1.0, 0.5 + (runoff_proxy - 0.35) / 0.35)
    elif runoff_proxy >= 0.25 and heavy_rain:
        pluvial = 0.45 + min(0.3, (runoff_proxy - 0.25) / 0.2)
    if heavy_rain and pluvial > 0:
        pluvial = min(1.0, pluvial + 0.1)

    low_lying = 0.0
    if floodplain is not None and floodplain >= 0.5:
        low_lying = max(low_lying, min(1.0, floodplain))
    if depression is not None and depression >= 0.15:
        low_lying = max(low_lying, min(1.0, depression / 0.3))
    if hand is not None and hand <= 5:
        low_lying = max(low_lying, 1.0 - hand / 5.0)
    if water_occurrence is not None and water_occurrence >= 10:
        low_lying = max(low_lying, min(1.0, water_occurrence / 50.0))
    if water_seasonality is not None and water_seasonality >= 1:
        low_lying = max(low_lying, 0.5)

    drainage = 0.0
    if runoff_proxy >= 0.3 and hand is not None and hand <= 10 and riverine < 0.35:
        drainage = min(1.0, runoff_proxy * (1.0 - hand / 10.0))
        if heavy_rain:
            drainage = min(1.0, drainage + 0.1)

    return {
        "riverine": round(riverine, 3),
        "pluvial": round(pluvial, 3),
        "low_lying": round(low_lying, 3),
        "drainage_constrained": round(drainage, 3),
    }


def classify_from_strengths(
    strengths: dict[str, float],
    *,
    min_strength: float = 0.2,
    mixed_band: float = 0.15,
    rationale_prefix: list[str] | None = None,
) -> FloodMechanismClassification:
    """Assign dominant flood mechanism type from precomputed strength scores."""
    ranked = sorted(strengths.items(), key=lambda kv: kv[1], reverse=True)
    top_name, top_val = ranked[0]
    second_val = ranked[1][1] if len(ranked) > 1 else 0.0
    rationale: list[str] = list(rationale_prefix or [])
    rationale.append(
        f"Strengths: riverine={strengths['riverine']}, pluvial={strengths['pluvial']}, "
        f"low_lying={strengths['low_lying']}, drainage={strengths['drainage_constrained']}."
    )

    if top_val < min_strength:
        mech_type: FloodMechanismType = "none"
        rationale.append(f"No mechanism ≥ {min_strength} — classified as none.")
    elif second_val >= top_val - mixed_band and second_val >= min_strength:
        mech_type = "mixed"
        tied = [k for k, v in strengths.items() if v >= top_val - mixed_band and v >= min_strength]
        rationale.append(f"Mixed: {', '.join(tied)} within {mixed_band} of top score.")
    else:
        mech_type = top_name  # type: ignore[assignment]
        rationale.append(f"Dominant: {mech_type} (strength={top_val:.2f}).")

    return FloodMechanismClassification(
        mechanism_type=mech_type,
        mechanism_code=FLOOD_MECHANISM_TYPE_CODES[mech_type],
        strengths=strengths,
        rationale=rationale,
    )


def classify_dominant_flood_mechanism(
    ctx: dict[str, Any],
    grid: dict[str, Any],
    water: dict[str, Any],
    *,
    min_strength: float = 0.2,
    mixed_band: float = 0.15,
) -> FloodMechanismClassification:
    """Assign a single dominant flood mechanism type per grid cell (ON-5990)."""
    strengths = flood_mechanism_strengths(ctx, grid, water)
    return classify_from_strengths(
        strengths,
        min_strength=min_strength,
        mixed_band=mixed_band,
    )


def score_flood_nbs(
    nbs_type: str,
    ctx: dict[str, Any],
    grid: dict[str, Any],
    water: dict[str, Any],
    mechanism: MechanismAssessment,
) -> NbsRecommendation:
    """Step 2 — simple rule scores per flood NBS typology."""
    risk = _get(ctx, "risk_mean", 0)
    imperv = _get(grid, "imperv_pct_mean", 0)
    dw_built = _get(grid, "dw_built_pct_mean")
    runoff_proxy = max(v for v in [imperv, dw_built, 0.0] if v is not None)
    green = _get(grid, "green_pct_mean", 0)
    open_land = _get(grid, "open_land_pct_mean", 0)
    flooded_vegetation = _get(grid, "dw_flooded_vegetation_pct_mean", 0)
    water_occurrence = _get(grid, "surface_water_occurrence_mean", 0)
    water_seasonality = _get(grid, "surface_water_seasonality_mean", 0)
    wet_transition = _get(grid, "surface_water_transition_wet_pct_mean", 0)
    heavy_rain = _heavy_rain_signal(grid)
    dist_river = _get(water, "dist_nearest_m", 9999)
    floodplain = _get(grid, "floodplain_adj_pct_mean", 0)
    depression = _get(grid, "depression_pct_mean", 0)
    slope = _get(grid, "slope_mean")
    if slope is None:
        slope = _get(grid, "slope_mean_mean")
    gaps: list[str] = []

    score = 0.0
    parts: list[str] = []

    if risk < 0.15:
        parts.append("Low flood priority for this bairro.")
    else:
        score += 0.25
        parts.append(f"Flood priority OK (risk_mean={risk:.2f}).")

    if nbs_type == "rain_garden":
        if mechanism.pluvial:
            score += 0.35
            parts.append("Pluvial mechanism supports distributed capture.")
        if runoff_proxy >= 0.3:
            score += 0.2
            parts.append(f"Runoff source proxy OK ({runoff_proxy:.2f}).")
        if heavy_rain:
            score += 0.1
            parts.append("CHIRPS heavy-rain proxy supports local capture.")
        if slope is not None and slope > 8:
            score -= 0.2
            parts.append(f"Steep slope may exclude (mean slope={slope:.1f}°).")
        elif slope is None:
            gaps.append("Slope not sampled — need `poa_slope` or Copernicus DEM COG.")
        gaps.extend(["SoilGrids infiltration not queried.", "Groundwater depth not available."])

    elif nbs_type == "bioswale":
        if mechanism.pluvial:
            score += 0.3
            parts.append("Pluvial / street runoff context.")
        if runoff_proxy >= 0.25:
            score += 0.25
            parts.append("Imperviousness supports interception.")
        if slope is not None and slope > 8:
            score -= 0.15
            parts.append(f"Mean slope {slope:.1f}° may constrain bioswale placement.")
        elif slope is None:
            gaps.append("Slope not sampled — need `poa_slope` or Copernicus DEM COG.")
        gaps.append("Linear ROW / road ownership — OSM proxy not queried per street segment.")

    elif nbs_type == "permeable_surfaces":
        if runoff_proxy >= 0.4:
            score += 0.4
            parts.append(f"High built/impervious proxy ({runoff_proxy:.2f}) — retrofit potential.")
        elif dw_built is not None:
            parts.append(f"Dynamic World built fraction ({dw_built:.2f}) refines GHSL screening.")
        gaps.append("Existing paving material still requires local survey.")

    elif nbs_type == "floodable_park":
        if mechanism.low_lying:
            score += 0.3
            parts.append("Low-lying / floodplain signal.")
        if open_land >= 0.25:
            score += 0.25
            parts.append(f"Open land proxy ({open_land:.2f}).")
        elif green >= 0.3:
            score += 0.25
            parts.append(f"Open/green land proxy ({green:.2f}).")
        else:
            parts.append("Limited open green fraction in screening cells — verify parcel scale.")
        if mechanism.riverine:
            score += 0.15
            parts.append("Near river — storage alongside waterfront.")

    elif nbs_type == "wetland_restoration":
        if mechanism.riverine or (dist_river is not None and dist_river < 800):
            score += 0.35
            parts.append("Hydrologic connection to drainage network.")
        if mechanism.low_lying or (depression is not None and depression > 0.1):
            score += 0.25
            parts.append("Depression / wetness signal.")
        if (
            water_occurrence >= 10
            or water_seasonality >= 1
            or wet_transition >= 0.1
            or flooded_vegetation >= 0.05
        ):
            score += 0.15
            parts.append("JRC/Dynamic World wetness history supports restoration screening.")
        gaps.append("Species / wetland inventory not queried.")

    elif nbs_type == "floodplain_restoration":
        if mechanism.riverine:
            score += 0.4
            parts.append("River proximity supports floodplain reconnection.")
        if floodplain >= 0.4:
            score += 0.2
            parts.append(f"Floodplain adjacency proxy ({floodplain:.2f}).")
        if open_land >= 0.25:
            score += 0.1
            parts.append(f"Open land proxy ({open_land:.2f}) supports corridor feasibility screening.")
        gaps.append("Cadastre / public land not confirmed.")

    elif nbs_type == "retention_basin":
        if mechanism.low_lying:
            score += 0.25
            parts.append("Low-lying context supports storage.")
        if open_land >= 0.25:
            score += 0.25
            parts.append(f"Potential storage space (open land={open_land:.2f}).")
        elif green >= 0.25:
            score += 0.25
            parts.append("Potential storage space (open land proxy).")
        if heavy_rain:
            score += 0.1
            parts.append("CHIRPS heavy-rain proxy supports detention need.")
        gaps.append("Parcel ownership unknown.")

    elif nbs_type == "riparian_buffer":
        if dist_river is not None and dist_river < 300:
            score += 0.45
            parts.append(f"Within ~{dist_river:.0f} m of waterway.")
        elif mechanism.riverine:
            score += 0.3
        if green >= 0.25:
            score += 0.1
            parts.append(f"Existing green cover proxy ({green:.2f}) supports corridor continuity.")

    score = max(0.0, min(1.0, score))
    label = "plausible" if score >= 0.55 else "weak" if score >= 0.35 else "unlikely"
    return NbsRecommendation(
        nbs_type=nbs_type,
        score=round(score, 2),
        rationale=f"{label}: " + " ".join(parts),
        gaps=gaps,
    )


FLOOD_NBS_TYPES = [
    "rain_garden",
    "bioswale",
    "permeable_surfaces",
    "floodable_park",
    "wetland_restoration",
    "floodplain_restoration",
    "retention_basin",
    "riparian_buffer",
]

NBS_TYPES = FLOOD_NBS_TYPES


def recommend_flood_all(
    ctx: dict[str, Any], grid: dict[str, Any], water: dict[str, Any]
) -> tuple[MechanismAssessment, list[NbsRecommendation]]:
    mechanism = infer_flood_mechanism(ctx, grid, water)
    recs = [score_flood_nbs(t, ctx, grid, water, mechanism) for t in FLOOD_NBS_TYPES]
    recs.sort(key=lambda r: r.score, reverse=True)
    return mechanism, recs


def infer_heat_mechanism(
    ctx: dict[str, Any], grid: dict[str, Any], water: dict[str, Any] | None = None
) -> HeatMechanismAssessment:
    """Step 1 — heat exposure context from diagnostic proxies."""
    _ = water  # reserved for riparian cooling corridor rules
    rationale: list[str] = []

    imperv = _get(grid, "imperv_pct_mean")
    dw_built = _get(grid, "dw_built_pct_mean")
    green = _get(grid, "green_pct_mean")
    tree = _get(grid, "tree_pct_mean")
    treecover = _get(grid, "treecover2000_mean")
    ndvi = _get(grid, "ndvi_mean")
    heat_hazard = _get(grid, "heat_score_mean") or _get(ctx, "hazard_mean")
    risk = _get(ctx, "risk_mean", 0)
    exposure = _get(ctx, "exposure_score", 0)
    vulnerability = _get(ctx, "vulnerability_score", 0)
    landsat = _normalize_lst_signal(_get(grid, "landsat_lst_norm_mean"))
    modis_day = _normalize_lst_signal(_get(grid, "modis_lst_day_norm_mean"))
    modis_night = _normalize_lst_signal(_get(grid, "modis_lst_night_norm_mean"))

    built_proxy = max(v for v in [imperv, dw_built, 0.0] if v is not None)
    veg_parts = [v for v in [green, tree, (ndvi / 100.0) if ndvi is not None else None] if v is not None]
    veg_proxy = max(veg_parts) if veg_parts else 0.0

    uhi_built_up = bool(built_proxy >= 0.35 and veg_proxy < 0.3)
    if uhi_built_up:
        rationale.append(
            f"UHI signal: built/impervious proxy {built_proxy:.2f}, vegetation proxy {veg_proxy:.2f}."
        )

    shade_deficit = bool(
        (tree is not None and tree < 0.15)
        or (treecover is not None and treecover < 20)
        or (green is not None and green < 0.25 and built_proxy >= 0.25)
    )
    if shade_deficit:
        rationale.append(
            f"Shade deficit: tree_pct={tree}, treecover2000={treecover}, green_pct={green}."
        )

    high_daytime_lst = bool(
        (heat_hazard is not None and heat_hazard >= 0.45)
        or (landsat is not None and landsat >= 0.55)
        or (modis_day is not None and modis_day >= 0.55)
    )
    if high_daytime_lst:
        rationale.append(
            f"High daytime LST proxy: heat_hazard={heat_hazard}, landsat_norm={landsat}, modis_day={modis_day}."
        )

    limited_nocturnal_cooling = bool(
        modis_night is not None
        and modis_day is not None
        and modis_night >= 0.5
        and (modis_night - modis_day) >= 0.05
    )
    if limited_nocturnal_cooling:
        rationale.append(
            f"Limited nocturnal cooling: MODIS night={modis_night:.2f}, day={modis_day:.2f}."
        )

    high_social_exposure = bool(
        risk >= 0.35 or exposure >= 0.5 or vulnerability >= 0.5
    )
    if high_social_exposure:
        rationale.append(
            f"Social exposure: risk={risk:.2f}, exposure={exposure:.2f}, vulnerability={vulnerability:.2f}."
        )

    if not rationale:
        rationale.append("No strong heat mechanism flags — screening signals are weak or missing.")

    return HeatMechanismAssessment(
        uhi_built_up=uhi_built_up,
        shade_deficit=shade_deficit,
        high_daytime_lst=high_daytime_lst,
        limited_nocturnal_cooling=limited_nocturnal_cooling,
        high_social_exposure=high_social_exposure,
        rationale=rationale,
    )


def heat_mechanism_strengths(
    ctx: dict[str, Any], grid: dict[str, Any], water: dict[str, Any] | None = None
) -> dict[str, float]:
    """Continuous 0–1 strength per heat mechanism type for grid-level classification."""
    _ = water
    imperv = _get(grid, "imperv_pct_mean")
    dw_built = _get(grid, "dw_built_pct_mean")
    green = _get(grid, "green_pct_mean")
    tree = _get(grid, "tree_pct_mean")
    treecover = _get(grid, "treecover2000_mean")
    ndvi = _get(grid, "ndvi_mean")
    heat_hazard = _get(grid, "heat_score_mean") or _get(ctx, "hazard_mean")
    risk = _get(ctx, "risk_mean", 0)
    exposure = _get(ctx, "exposure_score", 0)
    vulnerability = _get(ctx, "vulnerability_score", 0)
    landsat = _normalize_lst_signal(_get(grid, "landsat_lst_norm_mean"))
    modis_day = _normalize_lst_signal(_get(grid, "modis_lst_day_norm_mean"))
    modis_night = _normalize_lst_signal(_get(grid, "modis_lst_night_norm_mean"))

    built_proxy = max(v for v in [imperv, dw_built, 0.0] if v is not None)
    veg_parts = [v for v in [green, tree, (ndvi / 100.0) if ndvi is not None else None] if v is not None]
    veg_proxy = max(veg_parts) if veg_parts else 0.0

    uhi = 0.0
    if built_proxy >= 0.35 and veg_proxy < 0.3:
        uhi = min(1.0, 0.5 + (built_proxy - 0.35) / 0.4 + max(0.0, (0.3 - veg_proxy) / 0.3))
    elif built_proxy >= 0.25 and veg_proxy < 0.2:
        uhi = 0.35

    shade = 0.0
    if tree is not None and tree < 0.15:
        shade = max(shade, min(1.0, (0.15 - tree) / 0.15))
    if treecover is not None and treecover < 20:
        shade = max(shade, min(1.0, (20 - treecover) / 20))
    if green is not None and green < 0.25 and built_proxy >= 0.25:
        shade = max(shade, min(1.0, (0.25 - green) / 0.25 * built_proxy))

    daytime = 0.0
    if heat_hazard is not None and heat_hazard >= 0.45:
        daytime = max(daytime, min(1.0, (heat_hazard - 0.45) / 0.35))
    if landsat is not None and landsat >= 0.55:
        daytime = max(daytime, min(1.0, (landsat - 0.55) / 0.35))
    if modis_day is not None and modis_day >= 0.55:
        daytime = max(daytime, min(1.0, (modis_day - 0.55) / 0.35))

    nocturnal = 0.0
    if modis_night is not None and modis_day is not None and modis_night >= 0.5:
        delta = modis_night - modis_day
        if delta >= 0.05:
            nocturnal = min(1.0, 0.4 + delta / 0.2 + max(0.0, (modis_night - 0.5) / 0.3))

    social = 0.0
    if risk is not None and risk >= 0.35:
        social = max(social, min(1.0, (risk - 0.35) / 0.4))
    if exposure is not None and exposure >= 0.5:
        social = max(social, min(1.0, (exposure - 0.5) / 0.4))
    if vulnerability is not None and vulnerability >= 0.5:
        social = max(social, min(1.0, (vulnerability - 0.5) / 0.4))

    return {
        "uhi_built_up": round(uhi, 3),
        "shade_deficit": round(shade, 3),
        "high_daytime_lst": round(daytime, 3),
        "limited_nocturnal_cooling": round(nocturnal, 3),
        "high_social_exposure": round(social, 3),
    }


def classify_from_heat_strengths(
    strengths: dict[str, float],
    *,
    min_strength: float = HEAT_MIN_STRENGTH,
    mixed_band: float = 0.15,
    rationale_prefix: list[str] | None = None,
) -> HeatMechanismClassification:
    """Assign dominant heat mechanism type from precomputed strength scores."""
    ranked = sorted(strengths.items(), key=lambda kv: kv[1], reverse=True)
    top_name, top_val = ranked[0]
    second_val = ranked[1][1] if len(ranked) > 1 else 0.0
    rationale: list[str] = list(rationale_prefix or [])
    rationale.append(
        "Strengths: " + ", ".join(f"{k}={v}" for k, v in strengths.items()) + "."
    )

    if top_val < min_strength:
        mech_type: HeatMechanismType = "without_clear_dominant"
        rationale.append(
            f"No mechanism ≥ {min_strength} — without a clear dominant mechanism."
        )
    elif second_val >= top_val - mixed_band and second_val >= min_strength:
        mech_type = "mixed"
        tied = [k for k, v in strengths.items() if v >= top_val - mixed_band and v >= min_strength]
        rationale.append(f"Mixed: {', '.join(tied)} within {mixed_band} of top score.")
    else:
        mech_type = top_name  # type: ignore[assignment]
        rationale.append(f"Dominant: {mech_type} (strength={top_val:.2f}).")

    return HeatMechanismClassification(
        mechanism_type=mech_type,
        mechanism_code=HEAT_MECHANISM_TYPE_CODES[mech_type],
        strengths=strengths,
        rationale=rationale,
    )


def classify_dominant_heat_mechanism(
    ctx: dict[str, Any],
    grid: dict[str, Any],
    water: dict[str, Any] | None = None,
    *,
    min_strength: float = HEAT_MIN_STRENGTH,
    mixed_band: float = 0.15,
) -> HeatMechanismClassification:
    """Assign a single dominant heat mechanism type per grid cell (ON-5991)."""
    strengths = heat_mechanism_strengths(ctx, grid, water)
    return classify_from_heat_strengths(
        strengths,
        min_strength=min_strength,
        mixed_band=mixed_band,
    )


def score_heat_nbs(
    nbs_type: str,
    ctx: dict[str, Any],
    grid: dict[str, Any],
    mechanism: HeatMechanismAssessment,
    water: dict[str, Any] | None = None,
) -> NbsRecommendation:
    """Step 2 — simple rule scores per heat NBS typology."""
    risk = _get(ctx, "risk_mean", 0)
    hazard = _get(grid, "heat_score_mean") or _get(ctx, "hazard_mean", 0)
    imperv = _get(grid, "imperv_pct_mean", 0)
    dw_built = _get(grid, "dw_built_pct_mean")
    built_proxy = max(v for v in [imperv, dw_built, 0.0] if v is not None)
    green = _get(grid, "green_pct_mean", 0)
    open_land = _get(grid, "open_land_pct_mean", 0)
    tree = _get(grid, "tree_pct_mean", 0)
    slope = _get(grid, "slope_mean")
    clay = _get(grid, "clay_pct_mean")
    dist_water = _get((water or {}), "dist_nearest_m", 9999)
    gaps: list[str] = []

    score = 0.0
    parts: list[str] = []

    if risk < 0.15 and hazard < 0.35:
        parts.append("Low heat priority for this bairro.")
    else:
        score += 0.25
        parts.append(f"Heat priority OK (risk_mean={risk:.2f}, hazard={hazard:.2f}).")

    if nbs_type == "urban_street_trees":
        if mechanism.shade_deficit:
            score += 0.35
            parts.append("Shade deficit supports street-tree screening.")
        if mechanism.uhi_built_up:
            score += 0.2
            parts.append("Built-up / low-vegetation UHI context.")
        if open_land >= 0.1 or green >= 0.15:
            score += 0.1
            parts.append("Some planting space proxy along open/green land.")
        if slope is not None and slope > 12:
            score -= 0.15
            parts.append(f"Steep slope may limit pit stability (mean={slope:.1f}°).")
        gaps.extend(["OSM streets/ROW not queried.", "Underground utilities not mapped."])

    elif nbs_type == "green_corridor":
        if green >= 0.2:
            score += 0.3
            parts.append(f"Existing green fragments ({green:.2f}).")
        if mechanism.shade_deficit:
            score += 0.2
            parts.append("Shade deficit supports corridor expansion.")
        if built_proxy >= 0.35:
            score -= 0.1
            parts.append("Dense built environment may block continuous corridors.")
        gaps.append("Cadastre / public land not confirmed.")

    elif nbs_type == "pocket_park":
        if mechanism.high_social_exposure:
            score += 0.25
            parts.append("High exposure / vulnerability supports public-space cooling.")
        if open_land >= 0.2 or green >= 0.25:
            score += 0.3
            parts.append(f"Open land proxy ({open_land:.2f}) for pocket park space.")
        elif built_proxy >= 0.5:
            parts.append("Dense built block — parcel-scale open space may be limited.")
        gaps.append("Land cover ≠ ownership; parks layer not queried.")

    elif nbs_type == "schoolyard_greening":
        if mechanism.high_social_exposure:
            score += 0.3
            parts.append("Social exposure supports schoolyard targeting.")
        if open_land >= 0.15:
            score += 0.15
            parts.append("Some open land proxy in screening area.")
        gaps.extend(["OSM schools not queried.", "Schoolyard plantable area requires local parcel data."])

    elif nbs_type == "green_roof_wall":
        if built_proxy >= 0.45:
            score += 0.35
            parts.append(f"High built-up proxy ({built_proxy:.2f}) — rooftop retrofit context.")
        if mechanism.high_daytime_lst:
            score += 0.2
            parts.append("High LST supports surface-cooling interventions.")
        gaps.extend(["Roof structural capacity not available.", "Existing green roofs not mapped."])

    elif nbs_type == "riparian_cooling_corridor":
        if dist_water is not None and dist_water < 400:
            score += 0.35
            parts.append(f"Near waterway (~{dist_water:.0f} m) — riparian cooling potential.")
        if tree >= 0.1 or green >= 0.2:
            score += 0.15
            parts.append("Existing riparian vegetation proxy.")
        if mechanism.limited_nocturnal_cooling:
            score += 0.1
            parts.append("Nocturnal heat retention — waterfront vegetation may aid recovery.")
        gaps.append("Public access along riparian corridors not confirmed.")

    if clay is not None and clay >= 35 and nbs_type in {"urban_street_trees", "green_corridor", "pocket_park"}:
        parts.append(f"High clay ({clay:.1f}%) — check drainage / irrigation needs.")
    elif clay is None:
        gaps.append("SoilGrids clay (`soilgrids_clay`) not sampled.")

    score = max(0.0, min(1.0, score))
    label = "plausible" if score >= 0.55 else "weak" if score >= 0.35 else "unlikely"
    return NbsRecommendation(
        nbs_type=nbs_type,
        score=round(score, 2),
        rationale=f"{label}: " + " ".join(parts),
        gaps=gaps,
    )


HEAT_NBS_TYPES = [
    "urban_street_trees",
    "green_corridor",
    "pocket_park",
    "schoolyard_greening",
    "green_roof_wall",
    "riparian_cooling_corridor",
]


def recommend_heat_all(
    ctx: dict[str, Any],
    grid: dict[str, Any],
    water: dict[str, Any] | None = None,
) -> tuple[HeatMechanismAssessment, list[NbsRecommendation]]:
    mechanism = infer_heat_mechanism(ctx, grid, water)
    recs = [score_heat_nbs(t, ctx, grid, mechanism, water) for t in HEAT_NBS_TYPES]
    recs.sort(key=lambda r: r.score, reverse=True)
    return mechanism, recs


@dataclass
class LandslideMechanismAssessment:
    steep_activatable_slope: bool
    rainfall_trigger: bool
    low_cohesion_wet: bool
    vegetation_deficit: bool
    drainage_saturation: bool
    disturbed_bare_slope: bool
    upslope_convergence: bool
    high_social_exposure: bool
    rationale: list[str] = field(default_factory=list)


def infer_landslide_mechanism(
    ctx: dict[str, Any], grid: dict[str, Any], water: dict[str, Any] | None = None
) -> LandslideMechanismAssessment:
    """Step 1 — landslide susceptibility context from hazard ensemble proxies."""
    _ = water
    rationale: list[str] = []

    slope = _get(grid, "slope_mean")
    hazard = _get(grid, "landslide_score_mean") or _get(ctx, "hazard_mean")
    risk = _get(ctx, "risk_mean", 0)
    exposure = _get(ctx, "exposure_score", 0)
    vulnerability = _get(ctx, "vulnerability_score", 0)
    clay = _get(grid, "clay_pct_mean")
    ndvi_p10 = _get(grid, "ndvi_p10_mean")
    r90p = _get(grid, "r90p_climatology_mean") or _get(grid, "r90p_2024_mean")
    hand = _get(grid, "merit_hand_mean")
    upa = _get(grid, "upstream_area_km2_mean")
    bare = _get(grid, "dw_bare_pct_mean")
    built = _get(grid, "dw_built_pct_mean")
    green = _get(grid, "green_pct_mean")
    tree = _get(grid, "tree_pct_mean")
    dist_water = _get((water or {}), "dist_nearest_m", 9999)

    steep_activatable_slope = bool(
        (slope is not None and slope >= 15)
        or (hazard is not None and hazard > 0)
    )
    if steep_activatable_slope:
        rationale.append(
            f"Activatable slope signal: slope={slope}°, landslide_hazard={hazard} (methodology gate ≥15°)."
        )
    elif slope is not None and slope < 15:
        rationale.append(f"Slope {slope:.1f}° below 15° activation gate — flat/lowland screening context.")

    rainfall_trigger = bool(r90p is not None and r90p >= 200)
    if rainfall_trigger:
        rationale.append(f"Rainfall trigger proxy: R90p climatology={r90p:.1f} mm (regional chronic extreme rain).")

    low_cohesion_wet = bool(clay is not None and clay >= 35)
    if low_cohesion_wet:
        rationale.append(f"Low cohesion when wet: clay={clay:.1f}%.")

    vegetation_deficit = bool(
        (ndvi_p10 is not None and ndvi_p10 < 0.35)
        or (green is not None and green < 0.25)
        or (tree is not None and tree < 0.15)
    )
    if vegetation_deficit:
        rationale.append(
            f"Vegetation deficit: ndvi_p10={ndvi_p10}, green_pct={green}, tree_pct={tree}."
        )

    drainage_saturation = bool(
        (hand is not None and hand <= 5)
        or (dist_water is not None and dist_water < 200)
    )
    if drainage_saturation:
        rationale.append(
            f"Drainage saturation / convergence: HAND={hand}, dist_water={dist_water:.0f} m."
        )

    disturbed_bare_slope = bool(
        (bare is not None and bare >= 0.15) or (built is not None and built >= 0.25)
    )
    if disturbed_bare_slope:
        rationale.append(f"Disturbed/bare slope proxy: bare={bare}, built={built}.")

    upslope_convergence = bool(upa is not None and upa >= 1.0)
    if upslope_convergence:
        rationale.append(f"Upslope contributing area: UPA={upa:.2f} km².")

    high_social_exposure = bool(risk >= 0.03 or exposure >= 0.15 or vulnerability >= 0.25)
    if high_social_exposure:
        rationale.append(
            f"Social exposure: risk={risk:.3f}, exposure={exposure:.2f}, vulnerability={vulnerability:.2f}."
        )

    if not rationale:
        rationale.append("No strong landslide mechanism flags — screening signals weak or missing.")

    return LandslideMechanismAssessment(
        steep_activatable_slope=steep_activatable_slope,
        rainfall_trigger=rainfall_trigger,
        low_cohesion_wet=low_cohesion_wet,
        vegetation_deficit=vegetation_deficit,
        drainage_saturation=drainage_saturation,
        disturbed_bare_slope=disturbed_bare_slope,
        upslope_convergence=upslope_convergence,
        high_social_exposure=high_social_exposure,
        rationale=rationale,
    )


def landslide_mechanism_strengths(
    ctx: dict[str, Any], grid: dict[str, Any], water: dict[str, Any] | None = None
) -> dict[str, float]:
    """Continuous 0–1 strength per landslide mechanism type for grid-level classification."""
    slope = _get(grid, "slope_mean")
    hazard = _get(grid, "landslide_score_mean") or _get(ctx, "hazard_mean")
    risk = _get(ctx, "risk_mean", 0)
    exposure = _get(ctx, "exposure_score", 0)
    vulnerability = _get(ctx, "vulnerability_score", 0)
    clay = _get(grid, "clay_pct_mean")
    ndvi_p10 = _get(grid, "ndvi_p10_mean")
    r90p = _get(grid, "r90p_climatology_mean") or _get(grid, "r90p_2024_mean")
    hand = _get(grid, "merit_hand_mean")
    upa = _get(grid, "upstream_area_km2_mean")
    bare = _get(grid, "dw_bare_pct_mean")
    built = _get(grid, "dw_built_pct_mean")
    green = _get(grid, "green_pct_mean")
    tree = _get(grid, "tree_pct_mean")
    dist_water = _get((water or {}), "dist_nearest_m", 9999)

    steep = 0.0
    if slope is not None and slope >= 15:
        steep = min(1.0, 0.5 + (slope - 15) / 25)
    elif hazard is not None and hazard > 0:
        steep = min(1.0, max(0.2, hazard * 2))

    rainfall = 0.0
    if r90p is not None and r90p >= 200:
        rainfall = min(1.0, (r90p - 200) / 100)

    cohesion = 0.0
    if clay is not None and clay >= 35:
        cohesion = min(1.0, (clay - 35) / 25)

    veg = 0.0
    if ndvi_p10 is not None and ndvi_p10 < 0.35:
        veg = max(veg, min(1.0, (0.35 - ndvi_p10) / 0.35))
    if green is not None and green < 0.25:
        veg = max(veg, min(1.0, (0.25 - green) / 0.25))
    if tree is not None and tree < 0.15:
        veg = max(veg, min(1.0, (0.15 - tree) / 0.15))

    drainage = 0.0
    if hand is not None and hand <= 5:
        drainage = max(drainage, min(1.0, 1.0 - hand / 5.0))
    if dist_water is not None and dist_water < 200:
        drainage = max(drainage, min(1.0, 1.0 - dist_water / 200))

    bare_slope = 0.0
    if bare is not None and bare >= 0.15:
        bare_slope = max(bare_slope, min(1.0, (bare - 0.15) / 0.35))
    if built is not None and built >= 0.25:
        bare_slope = max(bare_slope, min(1.0, (built - 0.25) / 0.35))

    upslope = 0.0
    if upa is not None and upa >= 1.0:
        upslope = min(1.0, 0.4 + (upa - 1.0) / 5.0)

    social = 0.0
    if risk is not None and risk >= 0.03:
        social = max(social, min(1.0, (risk - 0.03) / 0.1))
    if exposure is not None and exposure >= 0.15:
        social = max(social, min(1.0, (exposure - 0.15) / 0.35))
    if vulnerability is not None and vulnerability >= 0.25:
        social = max(social, min(1.0, (vulnerability - 0.25) / 0.35))

    return {
        "steep_activatable_slope": round(steep, 3),
        "rainfall_trigger": round(rainfall, 3),
        "low_cohesion_wet": round(cohesion, 3),
        "vegetation_deficit": round(veg, 3),
        "drainage_saturation": round(drainage, 3),
        "disturbed_bare_slope": round(bare_slope, 3),
        "upslope_convergence": round(upslope, 3),
        "high_social_exposure": round(social, 3),
    }


def classify_from_landslide_strengths(
    strengths: dict[str, float],
    *,
    min_strength: float = LANDSLIDE_MIN_STRENGTH,
    mixed_band: float = 0.15,
    rationale_prefix: list[str] | None = None,
) -> LandslideMechanismClassification:
    """Assign dominant landslide mechanism type from precomputed strength scores."""
    ranked = sorted(strengths.items(), key=lambda kv: kv[1], reverse=True)
    top_name, top_val = ranked[0]
    second_val = ranked[1][1] if len(ranked) > 1 else 0.0
    rationale: list[str] = list(rationale_prefix or [])
    rationale.append(
        "Strengths: " + ", ".join(f"{k}={v}" for k, v in strengths.items()) + "."
    )

    if top_val < min_strength:
        mech_type: LandslideMechanismType = "without_clear_dominant"
        rationale.append(
            f"No mechanism ≥ {min_strength} — without a clear dominant mechanism."
        )
    elif second_val >= top_val - mixed_band and second_val >= min_strength:
        mech_type = "mixed"
        tied = [k for k, v in strengths.items() if v >= top_val - mixed_band and v >= min_strength]
        rationale.append(f"Mixed: {', '.join(tied)} within {mixed_band} of top score.")
    else:
        mech_type = top_name  # type: ignore[assignment]
        rationale.append(f"Dominant: {mech_type} (strength={top_val:.2f}).")

    return LandslideMechanismClassification(
        mechanism_type=mech_type,
        mechanism_code=LANDSLIDE_MECHANISM_TYPE_CODES[mech_type],
        strengths=strengths,
        rationale=rationale,
    )


def classify_dominant_landslide_mechanism(
    ctx: dict[str, Any],
    grid: dict[str, Any],
    water: dict[str, Any] | None = None,
    *,
    min_strength: float = LANDSLIDE_MIN_STRENGTH,
    mixed_band: float = 0.15,
) -> LandslideMechanismClassification:
    """Assign a single dominant landslide mechanism type per grid cell."""
    strengths = landslide_mechanism_strengths(ctx, grid, water)
    return classify_from_landslide_strengths(
        strengths,
        min_strength=min_strength,
        mixed_band=mixed_band,
    )


def score_landslide_nbs(
    nbs_type: str,
    ctx: dict[str, Any],
    grid: dict[str, Any],
    mechanism: LandslideMechanismAssessment,
    water: dict[str, Any] | None = None,
) -> NbsRecommendation:
    """Step 2 — simple rule scores per landslide NBS typology."""
    risk = _get(ctx, "risk_mean", 0)
    hazard = _get(grid, "landslide_score_mean") or _get(ctx, "hazard_mean", 0)
    slope = _get(grid, "slope_mean")
    clay = _get(grid, "clay_pct_mean")
    ndvi_p10 = _get(grid, "ndvi_p10_mean")
    green = _get(grid, "green_pct_mean", 0)
    bare = _get(grid, "dw_bare_pct_mean", 0)
    built = _get(grid, "dw_built_pct_mean", 0)
    hand = _get(grid, "merit_hand_mean")
    upa = _get(grid, "upstream_area_km2_mean")
    dist_water = _get((water or {}), "dist_nearest_m", 9999)
    gaps: list[str] = []

    score = 0.0
    parts: list[str] = []

    if hazard <= 0 and (slope is None or slope < 15):
        parts.append("Below slope activation gate — landslide NBS screening unlikely.")
    elif risk < 0.02 and hazard < 0.02:
        parts.append("Low landslide priority for this bairro.")
    else:
        score += 0.25
        parts.append(f"Landslide priority OK (risk={risk:.3f}, hazard={hazard:.3f}).")

    if not mechanism.steep_activatable_slope:
        score -= 0.2
        parts.append("Slope/hazard below activatable range for slope NBS.")

    if nbs_type == "slope_revegetation":
        if mechanism.vegetation_deficit:
            score += 0.35
            parts.append("Vegetation deficit supports revegetation screening.")
        if mechanism.steep_activatable_slope:
            score += 0.15
            parts.append("Activatable slope context.")
        if green >= 0.2:
            score += 0.1
            parts.append(f"Some existing cover ({green:.2f}) to build on.")
        if built >= 0.35:
            score -= 0.15
            parts.append("Built-up slope may limit planting — geotechnical review needed.")
        gaps.extend(["Geology not mapped.", "Root architecture / species not queried.", "Geotechnical survey required before design."])

    elif nbs_type == "bioengineering_erosion_control":
        if mechanism.disturbed_bare_slope:
            score += 0.35
            parts.append("Bare/disturbed slope supports erosion-control screening.")
        if mechanism.drainage_saturation or (hand is not None and hand <= 8):
            score += 0.2
            parts.append("Drainage-path / low HAND context.")
        if slope is not None and slope > 35:
            score -= 0.2
            parts.append(f"Slope {slope:.1f}° may exceed vegetation-only capacity.")
        gaps.extend(["OSM roads/access not queried per segment.", "Maintenance access not confirmed."])

    elif nbs_type == "riparian_gully_protection":
        if dist_water is not None and dist_water < 300:
            score += 0.35
            parts.append(f"Near drainage (~{dist_water:.0f} m).")
        if mechanism.drainage_saturation:
            score += 0.2
            parts.append("Low HAND / drainage convergence signal.")
        if green >= 0.15 or (ndvi_p10 is not None and ndvi_p10 >= 0.25):
            score += 0.1
            parts.append("Some riparian vegetation proxy present.")
        gaps.extend(["Riparian tenure not confirmed.", "Multi-hazard flood trade-offs not fully screened."])

    elif nbs_type == "forest_restoration_upslope":
        if mechanism.upslope_convergence:
            score += 0.3
            parts.append(f"Upslope area proxy (UPA={upa:.2f} km²).")
        if mechanism.vegetation_deficit:
            score += 0.2
            parts.append("Vegetation deficit supports upslope restoration.")
        if bare >= 0.1 or (ndvi_p10 is not None and ndvi_p10 < 0.4):
            score += 0.1
            parts.append("Degraded cover proxy.")
        gaps.extend(["Upslope land tenure not confirmed.", "Fire / multi-hazard context not screened."])

    if mechanism.low_cohesion_wet and clay is not None:
        parts.append(f"High clay ({clay:.1f}%) — species and drainage strategy need review.")
    elif clay is None:
        gaps.append("SoilGrids clay (`soilgrids_clay`) not sampled.")

    if mechanism.rainfall_trigger:
        parts.append("Chronic extreme rainfall context — drainage + cover NBS relevant.")

    score = max(0.0, min(1.0, score))
    label = "plausible" if score >= 0.55 else "weak" if score >= 0.35 else "unlikely"
    return NbsRecommendation(
        nbs_type=nbs_type,
        score=round(score, 2),
        rationale=f"{label}: " + " ".join(parts),
        gaps=gaps,
    )


LANDSLIDE_NBS_TYPES = [
    "slope_revegetation",
    "bioengineering_erosion_control",
    "riparian_gully_protection",
    "forest_restoration_upslope",
]


def recommend_landslide_all(
    ctx: dict[str, Any],
    grid: dict[str, Any],
    water: dict[str, Any] | None = None,
) -> tuple[LandslideMechanismAssessment, list[NbsRecommendation]]:
    mechanism = infer_landslide_mechanism(ctx, grid, water)
    recs = [score_landslide_nbs(t, ctx, grid, mechanism, water) for t in LANDSLIDE_NBS_TYPES]
    recs.sort(key=lambda r: r.score, reverse=True)
    return mechanism, recs


def recommend_all(
    ctx: dict[str, Any],
    grid: dict[str, Any],
    water: dict[str, Any],
    hazard: HazardKind = "flood",
) -> tuple[
    MechanismAssessment | HeatMechanismAssessment | LandslideMechanismAssessment,
    list[NbsRecommendation],
]:
    if hazard == "heat":
        return recommend_heat_all(ctx, grid, water)
    if hazard == "landslide":
        return recommend_landslide_all(ctx, grid, water)
    return recommend_flood_all(ctx, grid, water)


# Backward-compatible aliases
infer_mechanism = infer_flood_mechanism
score_nbs = score_flood_nbs
