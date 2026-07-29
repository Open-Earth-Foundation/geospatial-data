#!/usr/bin/env python3
"""Export Landsat 8 LST P90 + obs count + norm into heat_hazard data/input/.

Local geemap export is the default (no shard merge). For Drive multi-tile
exports, re-run with ``--merge-shards`` after shards land in data/input/.

Example:
  python transformation/landsat_lst/extract_landsat_lst.py --site plymouth
  python transformation/landsat_lst/extract_landsat_lst.py --site plymouth --qa-only
  python transformation/landsat_lst/extract_landsat_lst.py --site plymouth --merge-shards
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TRANSFORMATION = Path(__file__).resolve().parents[1]
HEAT_HAZARD = TRANSFORMATION / "heat_hazard"
if str(HEAT_HAZARD) not in sys.path:
    sys.path.insert(0, str(HEAT_HAZARD))

from gee_local_export import export_image_to_input  # noqa: E402
from input_common import (  # noqa: E402
    export_paths_summary,
    init_ee,
    load_heat_site,
    load_site_roi,
    minmax_norm_roi,
    season_months,
)
from qa_local import qa_landsat  # noqa: E402

SCALE_M = 30
NORM_SCALE_M = 300
CRS = "EPSG:4326"
MAX_CLOUD_LAND = 30
EXPORT_KEYS = ["landsat_p90", "landsat_obs_count", "landsat_norm"]
SHARD_RE = re.compile(r"^.+-\d{10}-\d{10}\.tif$", re.IGNORECASE)


def preprocess(image, ee):
    optical = image.select("SR_B.").multiply(0.0000275).add(-0.2)
    thermal = image.select("ST_B.*").multiply(0.00341802).add(149.0)
    scaled = image.addBands(optical, None, True).addBands(thermal, None, True)
    lst_c = scaled.select("ST_B10").subtract(273.15).rename("lst_celsius")
    with_lst = scaled.addBands(lst_c)
    qa = with_lst.select("QA_PIXEL")
    cloud_bits = (1 << 1) | (1 << 3) | (1 << 4)
    mask = qa.bitwiseAnd(cloud_bits).eq(0)
    return with_lst.updateMask(mask)


def resolve_gdal_tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for directory in (
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
        Path(os.environ.get("HOME", "")) / "homebrew" / "bin",
    ):
        candidate = directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise FileNotFoundError(f"Could not find `{name}` on PATH (install GDAL).")


def merge_shards_for_stem(input_dir: Path, stem: str) -> Path:
    out_tif = input_dir / f"{stem}.tif"
    shards = sorted(
        p for p in input_dir.glob(f"{stem}-*.tif") if SHARD_RE.match(p.name)
    )
    if out_tif.exists() and not shards:
        print(f"Already merged (no shards): {out_tif}")
        return out_tif
    if not shards:
        raise FileNotFoundError(
            f"No GEE shards for {stem!r} in {input_dir}. "
            f"Expected {stem}-0000000000-0000000000.tif"
        )

    gdalbuildvrt = resolve_gdal_tool("gdalbuildvrt")
    gdal_translate = resolve_gdal_tool("gdal_translate")
    print(f"Merging {len(shards)} shards → {out_tif.name}")
    with tempfile.TemporaryDirectory(prefix=f"{stem}_vrt_") as tmp:
        vrt_path = Path(tmp) / f"{stem}.vrt"
        subprocess.run([gdalbuildvrt, str(vrt_path), *[str(p) for p in shards]], check=True)
        tmp_out = input_dir / f".{stem}.merging.tif"
        if tmp_out.exists():
            tmp_out.unlink()
        subprocess.run(
            [
                gdal_translate,
                str(vrt_path),
                str(tmp_out),
                "-of",
                "GTiff",
                "-co",
                "COMPRESS=LZW",
                "-co",
                "TILED=YES",
                "-co",
                "BIGTIFF=YES",
                "-co",
                "NUM_THREADS=ALL_CPUS",
            ],
            check=True,
        )
        tmp_out.replace(out_tif)
    print(f"Wrote {out_tif}")
    return out_tif


def _maybe_qa(site: str, *, write_qa: bool) -> None:
    if not write_qa:
        return
    site_config = load_heat_site(site)
    display = site_config.get("display_name") or site
    input_dir = Path(site_config["paths_abs"]["data_input"])
    layers = site_config["layers"]
    qa_landsat(
        input_dir / layers["landsat_p90"],
        input_dir / layers["landsat_obs_count"],
        input_dir / layers["landsat_norm"],
        site_config,
        display=str(display),
    )


def run_merge_shards(site: str, *, write_qa: bool = True) -> list[Path]:
    site_config = load_heat_site(site)
    input_dir = Path(site_config["paths_abs"]["data_input"])
    layers = site_config["layers"]
    paths = []
    for key in ("landsat_p90", "landsat_norm"):
        stem = str(layers[key]).removesuffix(".tif")
        paths.append(merge_shards_for_stem(input_dir, stem))
    export_paths_summary(site_config, list(EXPORT_KEYS))
    _maybe_qa(site, write_qa=write_qa)
    return paths


def run(
    site: str,
    *,
    authenticate: bool = False,
    write_qa: bool = True,
    qa_only: bool = False,
) -> list[Path]:
    site_config = load_heat_site(site)
    display = site_config.get("display_name") or site
    input_dir = Path(site_config["paths_abs"]["data_input"])
    layers = site_config["layers"]
    paths = {key: input_dir / layers[key] for key in EXPORT_KEYS}

    if not qa_only:
        ee = init_ee(authenticate=authenticate)
        season = str(site_config.get("season") or "djf")
        season_label = str(site_config.get("season_label") or season.upper())
        start_year = int(site_config["start_year"])
        end_year = int(site_config["end_year"])
        months = season_months(site_config)
        roi = load_site_roi(site_config, ee)

        print(f"Landsat 8 LST → {display} ({site}) · {season_label} {start_year}–{end_year}")
        raw = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterDate(f"{start_year}-01-01", f"{end_year}-12-31")
            .filterBounds(roi)
            .map(lambda image: image.set("month", image.date().get("month")))
            .filter(ee.Filter.inList("month", months))
            .filter(ee.Filter.eq("PROCESSING_LEVEL", "L2SP"))
            .filter(ee.Filter.lte("CLOUD_COVER_LAND", MAX_CLOUD_LAND))
        )
        collection = raw.map(lambda img: preprocess(img, ee))
        print(f"Scenes in season filter: {collection.size().getInfo()}")

        lst_band = collection.select("lst_celsius")
        lst_p90 = lst_band.reduce(ee.Reducer.percentile([90])).rename("lst_p90_celsius").clip(roi)
        obs_count = lst_band.reduce(ee.Reducer.count()).rename("obs_count").clip(roi)
        lst_norm = minmax_norm_roi(
            lst_p90,
            band_name="lst_p90_celsius",
            roi=roi,
            ee=ee,
            scale=NORM_SCALE_M,
            out_name="lst_norm",
        )

        export_cfg = [
            (lst_p90, "landsat_p90"),
            (obs_count, "landsat_obs_count"),
            (lst_norm, "landsat_norm"),
        ]
        for image, key in export_cfg:
            export_image_to_input(
                image,
                filename=layers[key],
                region=roi,
                scale=SCALE_M,
                input_dir=input_dir,
                crs=CRS,
                description=Path(layers[key]).stem,
                drive_folder="EE_exports/heat",
            )
    else:
        missing = [str(p) for p in paths.values() if not p.is_file()]
        if missing:
            raise FileNotFoundError("Missing GeoTIFF(s) for --qa-only:\n  " + "\n  ".join(missing))

    export_paths_summary(site_config, EXPORT_KEYS)
    if write_qa:
        qa_landsat(
            paths["landsat_p90"],
            paths["landsat_obs_count"],
            paths["landsat_norm"],
            site_config,
            display=str(display),
        )
    return [paths[k] for k in EXPORT_KEYS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help="City slug (default: HEAT_SITE)")
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true", help="Skip SVG QA maps/hists")
    parser.add_argument(
        "--qa-only",
        action="store_true",
        help="Skip GEE export; rebuild QA from existing GeoTIFFs",
    )
    parser.add_argument(
        "--merge-shards",
        action="store_true",
        help="Only merge Drive export shards for landsat_p90 / landsat_norm (no GEE)",
    )
    args = parser.parse_args(argv)
    site = args.site or os.environ.get("HEAT_SITE") or os.environ.get("FLOODS_SITE", "porto_alegre")
    try:
        if args.merge_shards:
            paths = run_merge_shards(site, write_qa=not args.no_qa)
        else:
            paths = run(
                site,
                authenticate=args.authenticate,
                write_qa=not args.no_qa,
                qa_only=args.qa_only,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("\nDone:")
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
