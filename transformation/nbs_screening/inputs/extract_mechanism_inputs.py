#!/usr/bin/env python3
"""Run NBS mechanism screening input extractors for one hazard at a time.

Chains existing per-layer CLIs (D2–D8 + hazard input orchestrators) in a
hazard-specific order. Does **not** run flood + heat + landslide together unless
you pass multiple ``--hazard`` flags explicitly.

Examples:
  # Flood mechanism layers for one MN city
  python transformation/nbs_screening/inputs/extract_mechanism_inputs.py \\
    --hazard flood --site richfield

  # Heat inputs for all Minnesota cities
  python transformation/nbs_screening/inputs/extract_mechanism_inputs.py \\
    --hazard heat --country "United States"

  # Landslide — subset of steps
  python transformation/nbs_screening/inputs/extract_mechanism_inputs.py \\
    --hazard landslide --site plymouth --only landslide_inputs,merit_upa

  # Plan without GEE / Overpass
  python transformation/nbs_screening/inputs/extract_mechanism_inputs.py \\
    --hazard flood --site richfield --dry-run
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

INPUTS_ROOT = Path(__file__).resolve().parent
NBS_ROOT = INPUTS_ROOT.parent
TRANSFORMATION = NBS_ROOT.parent
REPO_ROOT = TRANSFORMATION.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def _runner_python() -> str:
    """Prefer repo venv (earthengine-api, rasterio) for child extract CLIs."""
    if VENV_PYTHON.is_file():
        return str(VENV_PYTHON)
    return sys.executable


if str(NBS_ROOT) not in sys.path:
    sys.path.insert(0, str(NBS_ROOT))

from site_config import resolve_site_slugs  # noqa: E402

HazardKind = Literal["flood", "heat", "landslide"]
HAZARDS: tuple[HazardKind, ...] = ("flood", "heat", "landslide")


@dataclass(frozen=True)
class ExtractStep:
    key: str
    script: Path
    extra_args: tuple[str, ...] = ()
    note: str = ""


def _step(key: str, rel: str, *extra_args: str, note: str = "") -> ExtractStep:
    return ExtractStep(key=key, script=TRANSFORMATION / rel, extra_args=extra_args, note=note)


HAZARD_STEPS: dict[HazardKind, tuple[ExtractStep, ...]] = {
    "flood": (
        _step("osm_rivers", "nbs_screening/floods/extract_osm_rivers.py", note="riverine distance"),
        _step(
            "dem_diagnostics",
            "copernicus_dem/compute_dem_diagnostics.py",
            note="relative elevation + depression",
        ),
        _step("merit_hydro", "merit_hydro/extract_merit_hydro.py", note="UPA + ELV"),
        _step("gsw", "jrc_global_surface_water/extract_gsw.py", note="JRC surface water"),
        _step("chirps_daily", "chirps_daily/extract_chirps_daily.py", note="RX1/RX5/R90p 2024"),
        _step("ghsl", "ghsl_built_up/extract_ghsl_built_up.py", note="impervious proxy"),
        _step("dynamic_world", "dynamic_world/extract_dw_mode.py", note="10 m + 250 m mode"),
        _step("slope", "copernicus_dem/extract_slope.py", note="poa_slope"),
        _step("clay", "soilgrids/extract_clay.py", note="soilgrids_clay"),
    ),
    "heat": (
        _step(
            "heat_inputs",
            "heat_hazard/extract_heat_inputs.py",
            note="MODIS + Landsat LST → heat_hazard/input",
        ),
        _step("ghsl", "ghsl_built_up/extract_ghsl_built_up.py"),
        _step("hansen", "hansen_forest_change/extract_treecover2000.py"),
        _step("ndvi_mean", "modis_ndvi/extract_ndvi_mean.py"),
        _step("slope", "copernicus_dem/extract_slope.py"),
        _step("clay", "soilgrids/extract_clay.py"),
    ),
    "landslide": (
        _step(
            "landslide_inputs",
            "landslide_hazard/extract_landslide_inputs.py",
            note="slope, HAND, clay, r90p clim, NDVI p10, DW",
        ),
        _step(
            "merit_upa",
            "merit_hydro/extract_merit_hydro.py",
            "--only",
            "upa",
            note="upstream area (grid optional)",
        ),
        _step("hansen", "hansen_forest_change/extract_treecover2000.py"),
    ),
}


@dataclass
class SiteHazardResult:
    site: str
    hazard: HazardKind
    ok: bool
    steps: dict[str, str] = field(default_factory=dict)
    error: str | None = None


def _parse_hazards(raw: list[str]) -> tuple[HazardKind, ...]:
    keys: list[str] = []
    for part in raw:
        keys.extend(k.strip() for k in part.split(",") if k.strip())
    valid = set(HAZARDS)
    unknown = [k for k in keys if k not in valid]
    if unknown:
        raise ValueError(f"Unknown hazard(s): {unknown}. Valid: {', '.join(HAZARDS)}")
    if not keys:
        raise ValueError("At least one --hazard is required.")
    # Preserve order, drop duplicates.
    seen: set[str] = set()
    ordered: list[HazardKind] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)  # type: ignore[arg-type]
    return tuple(ordered)


def _parse_only(raw: str | None, hazard: HazardKind) -> tuple[str, ...]:
    if not raw:
        return tuple(step.key for step in HAZARD_STEPS[hazard])
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    valid = {step.key for step in HAZARD_STEPS[hazard]}
    unknown = [k for k in keys if k not in valid]
    if unknown:
        known = ", ".join(sorted(valid))
        raise ValueError(f"Unknown step(s) for {hazard}: {unknown}. Valid: {known}")
    return tuple(keys)


def _build_cmd(
    step: ExtractStep,
    site: str,
    *,
    authenticate: bool,
    no_qa: bool,
    qa_only: bool,
    dry_run: bool,
) -> list[str]:
    cmd = [_runner_python(), str(step.script), "--site", site]
    cmd.extend(step.extra_args)
    if authenticate:
        cmd.append("--authenticate")
    if no_qa:
        cmd.append("--no-qa")
    if qa_only:
        cmd.append("--qa-only")
    if dry_run and step.script.name in {
        "compute_dem_diagnostics.py",
        "extract_osm_rivers.py",
        "extract_ghsl_built_up.py",
        "extract_merit_hydro.py",
        "extract_gsw.py",
        "extract_chirps_daily.py",
        "extract_treecover2000.py",
        "extract_ndvi_mean.py",
    }:
        cmd.append("--dry-run")
    return cmd


def _run_step(
    step: ExtractStep,
    site: str,
    *,
    authenticate: bool,
    no_qa: bool,
    qa_only: bool,
    dry_run: bool,
) -> tuple[str, str | None]:
    if not step.script.is_file():
        return "failed", f"missing script: {step.script}"

    cmd = _build_cmd(
        step,
        site,
        authenticate=authenticate,
        no_qa=no_qa,
        qa_only=qa_only,
        dry_run=dry_run,
    )
    label = step.note or step.script.name
    print(f"\n=== [{step.key}] {label} ===")
    print("  " + " ".join(cmd))

    if dry_run and "--dry-run" not in cmd:
        return "skipped", None

    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        return "failed", f"{step.key} exited {proc.returncode}"
    return "ok", None


def run_site_hazard(
    site: str,
    hazard: HazardKind,
    *,
    steps: tuple[str, ...],
    authenticate: bool,
    no_qa: bool,
    qa_only: bool,
    dry_run: bool,
) -> SiteHazardResult:
    step_map = {step.key: step for step in HAZARD_STEPS[hazard]}
    result = SiteHazardResult(site=site, hazard=hazard, ok=True)

    print(f"\n--- {hazard} inputs → {site} ---")
    print(f"Steps: {', '.join(steps)}")

    for key in steps:
        status, error = _run_step(
            step_map[key],
            site,
            authenticate=authenticate,
            no_qa=no_qa,
            qa_only=qa_only,
            dry_run=dry_run,
        )
        result.steps[key] = status
        if status == "failed":
            result.ok = False
            result.error = error
            break

    return result


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


def _print_summary(results: list[SiteHazardResult]) -> None:
    print("\n=== NBS mechanism input extract summary ===")
    for row in results:
        status = "OK" if row.ok else f"FAIL ({row.error})"
        print(f"  {row.site:<14} {row.hazard:<10} {status}")
        for key, step_status in row.steps.items():
            print(f"    [{key}] {step_status}")
    ok_n = sum(1 for r in results if r.ok)
    print(f"\nCompleted {ok_n}/{len(results)} site×hazard runs.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hazard",
        action="append",
        required=True,
        metavar="KIND",
        help=f"Hazard to extract (repeat or comma-separate). One of: {', '.join(HAZARDS)}",
    )
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
        help="Comma-separated subset of steps for the selected hazard(s)",
    )
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true")
    parser.add_argument("--qa-only", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        hazards = _parse_hazards(args.hazard)
        sites = _resolve_sites(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not sites:
        print("ERROR: no sites selected.", file=sys.stderr)
        return 1

    if args.only and len(hazards) != 1:
        print("ERROR: --only requires exactly one --hazard.", file=sys.stderr)
        return 1

    print(f"Using Python: {_runner_python()}")
    print(f"Sites ({len(sites)}): {', '.join(sites)}")
    print(f"Hazards: {', '.join(hazards)}")

    results: list[SiteHazardResult] = []
    for i, site in enumerate(sites, start=1):
        print(f"\n[{i}/{len(sites)}] site={site}")
        for hazard in hazards:
            try:
                steps = _parse_only(args.only, hazard)
            except ValueError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            results.append(
                run_site_hazard(
                    site,
                    hazard,
                    steps=steps,
                    authenticate=args.authenticate,
                    no_qa=args.no_qa,
                    qa_only=args.qa_only,
                    dry_run=args.dry_run,
                )
            )
            if not results[-1].ok and not args.continue_on_error and not args.dry_run:
                _print_summary(results)
                return 1

    _print_summary(results)

    if len(results) == 1 and results[0].ok and not args.dry_run:
        row = results[0]
        print(
            "\nNext: python transformation/nbs_screening/check_nbs_layers.py "
            f"--site {row.site} --hazard {row.hazard}"
        )
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
