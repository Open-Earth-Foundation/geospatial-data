"""Shared helpers for per-hazard NBS mechanism input extract CLIs."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

NBS_ROOT = Path(__file__).resolve().parent
TRANSFORMATION = NBS_ROOT.parent
REPO_ROOT = TRANSFORMATION.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

HazardKind = Literal["flood", "heat", "landslide"]

DRY_RUN_SCRIPTS = frozenset(
    {
        "compute_dem_diagnostics.py",
        "extract_osm_rivers.py",
        "extract_ghsl_built_up.py",
        "extract_merit_hydro.py",
        "extract_gsw.py",
        "extract_chirps_daily.py",
        "extract_treecover2000.py",
        "extract_ndvi_mean.py",
    }
)


def runner_python() -> str:
    """Prefer repo venv (earthengine-api, rasterio) for child extract CLIs."""
    if VENV_PYTHON.is_file():
        return str(VENV_PYTHON)
    return sys.executable


@dataclass(frozen=True)
class ExtractStep:
    key: str
    script: Path
    extra_args: tuple[str, ...] = ()
    note: str = ""


def make_step(key: str, rel: str, *extra_args: str, note: str = "") -> ExtractStep:
    return ExtractStep(key=key, script=TRANSFORMATION / rel, extra_args=extra_args, note=note)


@dataclass
class SiteRunResult:
    site: str
    hazard: HazardKind
    ok: bool
    steps: dict[str, str] = field(default_factory=dict)
    error: str | None = None


def parse_only(raw: str | None, steps: tuple[ExtractStep, ...]) -> tuple[str, ...]:
    if not raw:
        return tuple(step.key for step in steps)
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    valid = {step.key for step in steps}
    unknown = [k for k in keys if k not in valid]
    if unknown:
        known = ", ".join(sorted(valid))
        raise ValueError(f"Unknown step(s): {unknown}. Valid: {known}")
    return tuple(keys)


def build_cmd(
    step: ExtractStep,
    site: str,
    *,
    authenticate: bool,
    no_qa: bool,
    qa_only: bool,
    dry_run: bool,
) -> list[str]:
    cmd = [runner_python(), str(step.script), "--site", site]
    cmd.extend(step.extra_args)
    if authenticate:
        cmd.append("--authenticate")
    if no_qa:
        cmd.append("--no-qa")
    if qa_only:
        cmd.append("--qa-only")
    if dry_run and step.script.name in DRY_RUN_SCRIPTS:
        cmd.append("--dry-run")
    return cmd


def run_step(
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

    cmd = build_cmd(
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


def run_site(
    site: str,
    hazard: HazardKind,
    steps: tuple[ExtractStep, ...],
    *,
    step_keys: tuple[str, ...],
    authenticate: bool,
    no_qa: bool,
    qa_only: bool,
    dry_run: bool,
) -> SiteRunResult:
    step_map = {step.key: step for step in steps}
    result = SiteRunResult(site=site, hazard=hazard, ok=True)

    print(f"\n--- {hazard} mechanism inputs → {site} ---")
    print(f"Steps: {', '.join(step_keys)}")

    for key in step_keys:
        status, error = run_step(
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


def resolve_sites(args: argparse.Namespace) -> list[str]:
    if str(NBS_ROOT) not in sys.path:
        sys.path.insert(0, str(NBS_ROOT))
    from site_config import resolve_site_slugs

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


def add_site_selection_args(parser: argparse.ArgumentParser) -> None:
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


def add_extract_args(parser: argparse.ArgumentParser, steps: tuple[ExtractStep, ...]) -> None:
    parser.add_argument(
        "--only",
        default=None,
        help=f"Comma-separated subset of: {','.join(s.key for s in steps)}",
    )
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true")
    parser.add_argument("--qa-only", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")


def print_summary(results: list[SiteRunResult]) -> None:
    print("\n=== NBS mechanism input extract summary ===")
    for row in results:
        status = "OK" if row.ok else f"FAIL ({row.error})"
        print(f"  {row.site:<14} {row.hazard:<10} {status}")
        for key, step_status in row.steps.items():
            print(f"    [{key}] {step_status}")
    ok_n = sum(1 for r in results if r.ok)
    print(f"\nCompleted {ok_n}/{len(results)} sites.")


def run_cli(
    hazard: HazardKind,
    steps: tuple[ExtractStep, ...],
    *,
    argv: list[str] | None = None,
    doc: str,
    next_hint: str | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=doc)
    add_site_selection_args(parser)
    add_extract_args(parser, steps)
    args = parser.parse_args(argv)

    try:
        sites = resolve_sites(args)
        step_keys = parse_only(args.only, steps)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not sites:
        print("ERROR: no sites selected.", file=sys.stderr)
        return 1

    print(f"Using Python: {runner_python()}")
    print(f"Hazard: {hazard}")
    print(f"Sites ({len(sites)}): {', '.join(sites)}")

    results: list[SiteRunResult] = []
    for i, site in enumerate(sites, start=1):
        print(f"\n[{i}/{len(sites)}] site={site}")
        results.append(
            run_site(
                site,
                hazard,
                steps,
                step_keys=step_keys,
                authenticate=args.authenticate,
                no_qa=args.no_qa,
                qa_only=args.qa_only,
                dry_run=args.dry_run,
            )
        )
        if not results[-1].ok and not args.continue_on_error and not args.dry_run:
            print_summary(results)
            return 1

    print_summary(results)

    if len(results) == 1 and results[0].ok and not args.dry_run:
        hint = next_hint or (
            f"python transformation/nbs_screening/check_nbs_layers.py "
            f"--site {results[0].site} --hazard {hazard}"
        )
        print(f"\nNext: {hint}")

    return 0 if all(r.ok for r in results) else 1
