#!/usr/bin/env python3
"""Report NBS grid-screening layer readiness for a city site config.

Compares ``config/sites/{site}.yaml`` against files on disk (and S3 URLs for POA).
Use before running grid mechanism screening to see what still needs extraction.

Examples:
  python transformation/nbs_screening/check_nbs_layers.py --site richfield
  python transformation/nbs_screening/check_nbs_layers.py --site plymouth --hazard flood
  python transformation/nbs_screening/check_nbs_layers.py --all-mn
  python transformation/nbs_screening/check_nbs_layers.py --site richfield --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

NBS_ROOT = Path(__file__).resolve().parent
if str(NBS_ROOT) not in sys.path:
    sys.path.insert(0, str(NBS_ROOT))

from catalog_layers import (  # noqa: E402
    GRID_OPTIONAL_LAYER_KEYS,
    GRID_VALUE_LAYER_KEYS,
    HAZARD_REQUIRED_LAYERS,
    HazardKind,
)
from site_config import (  # noqa: E402
    DEFAULT_SITE,
    _layer_entry,
    load_site_config,
    merged_catalog_entries,
    reference_hazard_layer,
    resolve_osm_rivers_path,
)

LayerStatus = Literal["ready_local", "ready_url", "missing_local", "unconfigured"]

MN_SITES = ("apple_valley", "edina", "plymouth", "richfield", "rochester")
HAZARDS: tuple[HazardKind, ...] = ("flood", "heat", "landslide")
CATALOG_SECTIONS = ("shared", *HAZARDS)


@dataclass
class LayerCheck:
    layer_id: str
    section: str
    status: LayerStatus
    configured_local: str | None
    configured_url: str | None
    resolved: str | None
    required_for_hazard: bool
    used_in_grid_screening: bool


def _local_path(repo_root: Path, rel: str) -> Path:
    path = Path(rel).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path


def _grid_layer_ids(hazard: HazardKind) -> set[str]:
    ids = set(GRID_VALUE_LAYER_KEYS[hazard].values())
    ids.update(GRID_OPTIONAL_LAYER_KEYS.get(hazard, {}).values())
    return ids


def _check_entry(
    layer_id: str,
    section: str,
    entry: Any,
    *,
    repo_root: Path,
    hazard: HazardKind | None,
) -> LayerCheck:
    spec = _layer_entry(entry)
    local_rel = spec.get("local")
    url = spec.get("url")
    local_path = _local_path(repo_root, str(local_rel)) if local_rel else None
    local_exists = local_path is not None and local_path.is_file()

    if local_exists:
        status: LayerStatus = "ready_local"
        resolved = str(local_path.resolve())
    elif url:
        status = "ready_url"
        resolved = str(url)
    elif local_rel:
        status = "missing_local"
        resolved = None
    else:
        status = "unconfigured"
        resolved = None

    required = hazard is not None and layer_id in HAZARD_REQUIRED_LAYERS[hazard]
    used = hazard is not None and layer_id in _grid_layer_ids(hazard)

    return LayerCheck(
        layer_id=layer_id,
        section=section,
        status=status,
        configured_local=str(local_rel) if local_rel else None,
        configured_url=str(url) if url else None,
        resolved=resolved,
        required_for_hazard=required,
        used_in_grid_screening=used,
    )


def audit_site(
    site: str,
    *,
    hazard: HazardKind | None = None,
    by_section: bool = False,
) -> dict[str, Any]:
    config = load_site_config(site)
    repo_root = Path(config["repo_root"])
    catalog = config.get("catalog") or {}

    hazards = (hazard,) if hazard else HAZARDS
    checks: list[LayerCheck] = []

    if by_section:
        for section in CATALOG_SECTIONS:
            hazard_ctx = section if section in HAZARDS else None
            for layer_id, entry in (catalog.get(section) or {}).items():
                checks.append(
                    _check_entry(
                        layer_id,
                        section,
                        entry,
                        repo_root=repo_root,
                        hazard=hazard_ctx if hazard_ctx in hazards else None,
                    )
                )
    else:
        for hz in hazards:
            for layer_id, entry in merged_catalog_entries(config, hz).items():
                checks.append(
                    _check_entry(
                        layer_id,
                        hz,
                        entry,
                        repo_root=repo_root,
                        hazard=hz,
                    )
                )

    ref_layer = {hz: reference_hazard_layer(hz, config) for hz in hazards}
    ref_ready = {}
    for hz in hazards:
        ref_id = ref_layer[hz]
        match = next((c for c in checks if c.section == hz and c.layer_id == ref_id), None)
        ref_ready[hz] = match.status if match else "unconfigured"

    ready = [c for c in checks if c.status.startswith("ready")]
    missing = [c for c in checks if c.status == "missing_local"]
    required_missing = [
        c for c in checks if c.required_for_hazard and c.status == "missing_local"
    ]
    grid_missing = [
        c
        for c in checks
        if c.used_in_grid_screening and c.status == "missing_local"
    ]

    osm_cfg = config.get("osm_waterways") or {}
    osm_local = osm_cfg.get("local")
    osm_resolved = resolve_osm_rivers_path(site)
    osm_ready = osm_resolved is not None

    return {
        "site": site,
        "display_name": config.get("display_name"),
        "config_path": str(config["config_path"]),
        "hazards": list(hazards),
        "by_section": by_section,
        "reference_hazard": ref_layer,
        "reference_hazard_ready": ref_ready,
        "osm_waterways": {
            "configured_local": str(osm_local) if osm_local else None,
            "resolved": str(osm_resolved) if osm_resolved else None,
            "ready": osm_ready,
        },
        "summary": {
            "total": len(checks),
            "ready": len(ready),
            "missing_local": len(missing),
            "required_missing": len(required_missing),
            "grid_screening_missing": len(grid_missing),
            "osm_waterways_ready": osm_ready,
        },
        "layers": [asdict(c) for c in checks],
        "missing_local": [asdict(c) for c in missing],
        "required_missing": [asdict(c) for c in required_missing],
    }


def _status_icon(status: LayerStatus) -> str:
    return {
        "ready_local": "OK ",
        "ready_url": "URL",
        "missing_local": "MISS",
        "unconfigured": "----",
    }[status]


def _print_report(report: dict[str, Any], *, verbose: bool) -> None:
    summary = report["summary"]
    print(f"\n{report['display_name']} ({report['site']})")
    print(f"  config: {report['config_path']}")
    print(
        f"  layers: {summary['ready']}/{summary['total']} ready"
        f" · {summary['missing_local']} missing on disk"
    )
    if summary["required_missing"]:
        print(f"  !! {summary['required_missing']} required hazard layer(s) missing")
    for hz, layer_id in report["reference_hazard"].items():
        status = report["reference_hazard_ready"][hz]
        print(f"  ref grid {hz}: {layer_id} → {status}")

    osm = report.get("osm_waterways") or {}
    osm_status = "ready" if osm.get("ready") else "MISSING (run extract_osm_rivers.py)"
    print(f"  osm_waterways: {osm_status}")
    if osm.get("configured_local") and not osm.get("ready"):
        print(f"    expected: {osm['configured_local']}")
    elif osm.get("resolved"):
        print(f"    path: {osm['resolved']}")

    if verbose:
        print("\n  layer_id                          status  section   grid  req")
        for row in report["layers"]:
            grid = "Y" if row["used_in_grid_screening"] else "-"
            req = "Y" if row["required_for_hazard"] else "-"
            print(
                f"  {row['layer_id']:<32}  {_status_icon(row['status'])}  "
                f"{row['section']:<9} {grid:>4}  {req:>3}"
            )
    elif report["missing_local"]:
        print("\n  missing (local path configured, file absent):")
        seen: set[tuple[str, str | None]] = set()
        for row in report["missing_local"]:
            key = (row["layer_id"], row["configured_local"])
            if key in seen:
                continue
            seen.add(key)
            hazards = sorted(
                {
                    r["section"]
                    for r in report["missing_local"]
                    if r["layer_id"] == row["layer_id"]
                    and r["configured_local"] == row["configured_local"]
                }
            )
            tag = ""
            if any(r["required_for_hazard"] for r in report["missing_local"] if r["layer_id"] == row["layer_id"]):
                tag = " [required]"
            elif any(r["used_in_grid_screening"] for r in report["missing_local"] if r["layer_id"] == row["layer_id"]):
                tag = " [grid]"
            hz = ",".join(hazards)
            print(f"    - {row['layer_id']} ({hz}){tag}")
            if row["configured_local"]:
                print(f"      {row['configured_local']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help=f"City slug (default: {DEFAULT_SITE} or NBS_SITE)")
    parser.add_argument(
        "--all-mn",
        action="store_true",
        help=f"Check all Minnesota sites: {', '.join(MN_SITES)}",
    )
    parser.add_argument(
        "--hazard",
        choices=[*HAZARDS, "all"],
        default="all",
        help="Hazard profile to check (default: all)",
    )
    parser.add_argument(
        "--by-section",
        action="store_true",
        help="Report by YAML section (shared/flood/heat/landslide) instead of merged hazard profiles",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    parser.add_argument("-v", "--verbose", action="store_true", help="List every layer")
    args = parser.parse_args(argv)

    if args.all_mn:
        sites = list(MN_SITES)
    else:
        sites = [args.site or os.environ.get("NBS_SITE", DEFAULT_SITE)]

    hazard = None if args.hazard == "all" else args.hazard
    reports = [audit_site(site, hazard=hazard, by_section=args.by_section) for site in sites]

    if args.json:
        payload = reports[0] if len(reports) == 1 else reports
        print(json.dumps(payload, indent=2))
    else:
        for report in reports:
            _print_report(report, verbose=args.verbose)

    exit_code = 0
    for report in reports:
        if report["summary"]["required_missing"]:
            exit_code = 1
        ref = report["reference_hazard_ready"]
        if any(status == "missing_local" for status in ref.values()):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
