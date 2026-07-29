#!/usr/bin/env python3
"""Export CHIRPS seasonal R90p climatology into landslide_hazard data/input/.

Example:
  python transformation/chirps_r90p/extract_chirps_r90p.py --site plymouth
  python transformation/chirps_r90p/extract_chirps_r90p.py --site plymouth --qa-only
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

TRANSFORMATION = Path(__file__).resolve().parents[1]
LS = TRANSFORMATION / "landslide_hazard"
if str(LS) not in sys.path:
    sys.path.insert(0, str(LS))

from input_common import (  # noqa: E402
    export_paths_summary,
    init_ee,
    load_landslide_site,
    load_site_roi,
    reexec_with_repo_venv_if_needed,
    season_month_filter,
)

reexec_with_repo_venv_if_needed("numpy", "rasterio")

from gee_local_export import export_image_to_input  # noqa: E402
from qa_local import qa_r90p  # noqa: E402


def run(
    site: str,
    *,
    authenticate: bool = False,
    write_qa: bool = True,
    qa_only: bool = False,
) -> Path:
    cfg = load_landslide_site(site)
    display = cfg.get("display_name") or site
    input_dir = Path(cfg["paths_abs"]["data_input"])
    filename = cfg["layers"]["r90p"]
    out_path = input_dir / filename

    if not qa_only:
        ee = init_ee(authenticate=authenticate)
        season = str(cfg["season"])
        season_label = str(cfg.get("season_label") or season.upper())
        start_year = int(cfg["start_year"])
        end_year = int(cfg["end_year"])
        roi = load_site_roi(cfg, ee)

        print(f"CHIRPS R90p → {display} ({site}) · {season_label} {start_year}–{end_year}")
        chirps = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterBounds(roi)
            .filterDate(f"{start_year}-01-01", f"{end_year}-12-31")
            .filter(season_month_filter(ee, season))
        )
        print(f"{season_label} CHIRPS days: {chirps.size().getInfo()}")
        r90p = (
            chirps.reduce(ee.Reducer.percentile([90]))
            .rename("r90p")
            .clip(roi)
            .reproject(crs="EPSG:4326", scale=5000)
            .toFloat()
        )
        export_image_to_input(
            r90p,
            filename=filename,
            region=roi,
            scale=5000,
            input_dir=input_dir,
            crs="EPSG:4326",
            description=Path(filename).stem,
            drive_folder="gee_exports",
        )
    elif not out_path.is_file():
        raise FileNotFoundError(f"Missing GeoTIFF for --qa-only: {out_path}")

    export_paths_summary(cfg, ["r90p"])
    if write_qa:
        qa_r90p(out_path, cfg, display=str(display))
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None)
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true")
    parser.add_argument("--qa-only", action="store_true")
    args = parser.parse_args(argv)
    site = (
        args.site
        or os.environ.get("LANDSLIDES_SITE")
        or os.environ.get("FLOODS_SITE", "porto_alegre")
    )
    try:
        out = run(
            site,
            authenticate=args.authenticate,
            write_qa=not args.no_qa,
            qa_only=args.qa_only,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"\nDone: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
