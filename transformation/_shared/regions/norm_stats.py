"""Load versioned CCRA regional normalization stats (Option 1 dual-product)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGIONS_DIR = Path(__file__).resolve().parent
REPO_ROOT = REGIONS_DIR.parents[2]  # geospatial-data/


def repo_root() -> Path:
    return REPO_ROOT


def default_stats_path(region_id: str, stats_version: str = "v1") -> Path:
    return (
        REPO_ROOT
        / "cache"
        / "regions"
        / region_id
        / "normalization"
        / stats_version
        / "normalization_stats.json"
    )


def load_norm_stats(
    region_id: str,
    *,
    stats_version: str = "v1",
    path: Path | None = None,
    require_ready: bool = False,
) -> dict[str, Any]:
    stats_path = Path(path) if path else default_stats_path(region_id, stats_version)
    if not stats_path.is_file():
        raise FileNotFoundError(
            f"Regional norm stats not found: {stats_path}. "
            f"Run compute_regional_norm_stats.py --region {region_id} first."
        )
    payload = json.loads(stats_path.read_text(encoding="utf-8"))
    if payload.get("region_id") != region_id:
        raise ValueError(
            f"stats region_id={payload.get('region_id')!r} does not match {region_id!r}"
        )
    status = payload.get("status") or "pending"
    if require_ready and status != "ready":
        raise ValueError(
            f"Stats status is {status!r} (need ready). path={stats_path}"
        )
    return payload


def layer_minmax(stats: dict[str, Any], layer_key: str) -> tuple[float, float]:
    layers = stats.get("layers") or {}
    row = layers.get(layer_key)
    if not isinstance(row, dict):
        raise KeyError(f"Layer {layer_key!r} missing from regional stats")
    if row.get("method") != "minmax":
        raise ValueError(f"Layer {layer_key!r} method is {row.get('method')!r}, expected minmax")
    vmin, vmax = row.get("vmin"), row.get("vmax")
    if vmin is None or vmax is None:
        raise ValueError(f"Layer {layer_key!r} has null vmin/vmax (status incomplete)")
    lo, hi = float(vmin), float(vmax)
    if lo != lo or hi != hi:  # NaN
        raise ValueError(f"Layer {layer_key!r} has NaN vmin/vmax")
    if hi <= lo:
        raise ValueError(f"Layer {layer_key!r} invalid range vmin={lo} vmax={hi}")
    return lo, hi


def save_norm_stats(payload: dict[str, Any], path: Path | None = None) -> Path:
    region_id = str(payload["region_id"])
    stats_version = str(payload.get("stats_version") or "v1")
    out = Path(path) if path else default_stats_path(region_id, stats_version)
    out.parent.mkdir(parents=True, exist_ok=True)
    layers = payload.get("layers") or {}
    filled = 0
    total = 0
    for row in layers.values():
        if not isinstance(row, dict):
            continue
        total += 1
        method = row.get("method")
        if method == "minmax" and row.get("vmin") is not None and row.get("vmax") is not None:
            filled += 1
        elif method == "robust_p95_log1p_minmax" and row.get("p95") is not None:
            filled += 1
    if filled == 0:
        payload["status"] = "pending"
    elif filled < total:
        payload["status"] = "partial"
    else:
        payload["status"] = "ready"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def update_layer_stats(
    payload: dict[str, Any],
    layer_key: str,
    *,
    vmin: float,
    vmax: float,
    method: str = "minmax",
    unit: str | None = None,
    n_samples: int | None = None,
    notes: str | None = None,
    **extra: Any,
) -> None:
    layers = dict(payload.get("layers") or {})
    row = dict(layers.get(layer_key) or {})
    row["method"] = method
    if unit:
        row["unit"] = unit
    row["vmin"] = float(vmin)
    row["vmax"] = float(vmax)
    if n_samples is not None:
        row["n_samples"] = int(n_samples)
    if notes is not None:
        row["notes"] = notes
    row.update(extra)
    layers[layer_key] = row
    payload["layers"] = layers
