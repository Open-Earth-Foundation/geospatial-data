#!/usr/bin/env python3
"""Run all flood hazard input extractors for one city (GEE → data/input/).

Order: GFPLAIN → JRC → Aqueduct → GFD (reference grid first, then fluvial, then GFD).
Each extractor also writes local QA SVGs under ``data/intermediate/qa_inputs/``.

When ``CCRA_REGIONAL_CACHE`` points at a batch ``cache/regions/...`` directory that
already has ``layers/*.tif``, GFPLAIN / JRC / Aqueduct are **clipped from the
regional cache** (no per-city GEE call). GFD still uses the city extractor
(city-domain robust norm).

Example:
  python transformation/flood_hazard/extract_flood_inputs.py --site plymouth
  python transformation/flood_hazard/extract_flood_inputs.py --site plymouth --only gfplain,jrc
  CCRA_REGIONAL_CACHE=cache/regions/minnesota/minnesota-metro-5 \\
    python transformation/flood_hazard/extract_flood_inputs.py --site edina
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

FLOOD_HAZARD_ROOT = Path(__file__).resolve().parent
TRANSFORMATION = FLOOD_HAZARD_ROOT.parent

EXTRACTORS: dict[str, Path] = {
    "gfplain": TRANSFORMATION / "gfplain250m" / "extract_gfplain.py",
    "jrc": TRANSFORMATION / "jrc_global_river_flood_hazard_maps" / "extract_jrc.py",
    "aqueduct": TRANSFORMATION / "wri_aqueduct" / "extract_aqueduct.py",
    "gfd": TRANSFORMATION / "global_flood_database" / "extract_gfd.py",
}
DEFAULT_ORDER = ["gfplain", "jrc", "aqueduct", "gfd"]
REGIONAL_CLIP_SOURCES = {"gfplain", "jrc", "aqueduct"}


def _try_regional_clip(site: str, keys: list[str], *, write_qa: bool) -> set[str]:
    """Clip regional layers for requested keys. Returns sources satisfied from cache."""
    cache = (os.environ.get("CCRA_REGIONAL_CACHE") or "").strip()
    if not cache:
        return set()
    cache_dir = Path(cache)
    layers_dir = cache_dir / "layers"
    if not layers_dir.is_dir():
        print(f"[regional-clip] no layers/ under {cache_dir}; falling back to GEE")
        return set()

    if str(TRANSFORMATION) not in sys.path:
        sys.path.insert(0, str(TRANSFORMATION))
    from ccra_batch.clip_to_site import materialize_city_flood_inputs
    from ccra_batch.regional_layers import available_regional_sources
    from input_common import load_flood_site

    available = available_regional_sources(cache_dir)
    wanted = [k for k in keys if k in REGIONAL_CLIP_SOURCES and k in available]
    if not wanted:
        return set()

    site_config = load_flood_site(site)
    print(f"[regional-clip] using {cache_dir} for sources={wanted}")
    written = materialize_city_flood_inputs(layers_dir, site_config)
    satisfied = set()
    # Map layer keys back to source names
    key_to_source = {
        "gfplain": "gfplain",
        "jrc_depth": "jrc",
        "jrc_norm": "jrc",
        "aqueduct_depth": "aqueduct",
        "aqueduct_norm": "aqueduct",
    }
    for layer_key in written:
        src = key_to_source.get(layer_key)
        if src in wanted:
            satisfied.add(src)

    # Only count a source satisfied when all its expected layer keys landed.
    need = {
        "gfplain": {"gfplain"},
        "jrc": {"jrc_depth", "jrc_norm"},
        "aqueduct": {"aqueduct_depth", "aqueduct_norm"},
    }
    fully = {s for s in satisfied if need[s].issubset(set(written))}

    if write_qa and fully:
        # Rebuild QA from clipped TIFFs via extractor --qa-only.
        for key in fully:
            script = EXTRACTORS[key]
            cmd = [sys.executable, str(script), "--site", site, "--qa-only"]
            print(f"\n=== {key} QA from regional clip: {script.name} ===")
            subprocess.run(cmd, check=False)

    return fully


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help="City slug (default: FLOODS_SITE)")
    parser.add_argument(
        "--only",
        default=None,
        help=f"Comma-separated subset of: {','.join(DEFAULT_ORDER)}",
    )
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true", help="Skip SVG QA on extractors")
    parser.add_argument(
        "--qa-only",
        action="store_true",
        help="Skip GEE export; rebuild QA from existing GeoTIFFs",
    )
    parser.add_argument(
        "--regional-cache",
        default=None,
        help="Batch cache dir with layers/ (else CCRA_REGIONAL_CACHE env)",
    )
    args = parser.parse_args(argv)

    if args.regional_cache:
        os.environ["CCRA_REGIONAL_CACHE"] = str(Path(args.regional_cache).resolve())

    site = args.site or os.environ.get("FLOODS_SITE", "porto_alegre")
    keys = DEFAULT_ORDER
    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
        unknown = [k for k in keys if k not in EXTRACTORS]
        if unknown:
            print(f"ERROR: unknown extractors: {unknown}", file=sys.stderr)
            return 1

    print(f"Extracting flood inputs for site={site}: {keys}")
    satisfied: set[str] = set()
    if not args.qa_only:
        satisfied = _try_regional_clip(site, keys, write_qa=not args.no_qa)

    for key in keys:
        if key in satisfied and not args.qa_only:
            print(f"\n=== {key}: skipped GEE (regional clip) ===")
            continue
        script = EXTRACTORS[key]
        cmd = [sys.executable, str(script), "--site", site]
        if args.authenticate:
            cmd.append("--authenticate")
        if args.no_qa:
            cmd.append("--no-qa")
        if args.qa_only:
            cmd.append("--qa-only")
        print(f"\n=== {key}: {script.name} ===")
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(f"ERROR: {key} failed with exit {result.returncode}", file=sys.stderr)
            return result.returncode

    print("\nAll flood input extracts finished.")
    print(f"QA SVGs (if enabled): flood_hazard/sites/{site}/data/intermediate/qa_inputs/")
    print(
        "Next: python transformation/flood_hazard/compute_flood_hazard.py "
        f"--site {site}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
