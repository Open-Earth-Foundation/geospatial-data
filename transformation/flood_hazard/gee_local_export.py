"""Export Earth Engine images directly into a flood_hazard site input folder.

Default mode writes GeoTIFFs under ``sites/<city>/data/input/`` (gitignored).
Optional fallback: ``GEE_EXPORT_MODE=drive`` keeps the legacy Google Drive path.

City-scale AOIs (e.g. Plymouth) fit local export well. Very large AOIs may hit
Earth Engine download size limits — switch to Drive/GCS or tile the export.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def export_mode() -> str:
    """Return ``local`` (default) or ``drive``."""
    return (os.environ.get("GEE_EXPORT_MODE") or "local").strip().lower()


def export_image_to_input(
    image: Any,
    *,
    filename: str,
    region: Any,
    scale: float | int,
    input_dir: Path,
    crs: str = "EPSG:4326",
    description: str | None = None,
    drive_folder: str = "gee_exports",
) -> Path | Any:
    """Export one EE image to ``input_dir/filename`` (local) or Google Drive.

    Returns
    -------
    Path
        Local GeoTIFF path when ``GEE_EXPORT_MODE=local``.
    ee.batch.Task
        Started Drive export task when ``GEE_EXPORT_MODE=drive``.
    """
    input_dir = Path(input_dir)
    input_dir.mkdir(parents=True, exist_ok=True)
    out_path = input_dir / filename
    mode = export_mode()
    desc = description or Path(filename).stem

    if mode in {"drive", "todrive", "google_drive"}:
        import ee

        task = ee.batch.Export.image.toDrive(
            image=image,
            description=desc[:100],
            folder=drive_folder,
            fileNamePrefix=Path(filename).stem,
            region=region,
            scale=scale,
            crs=crs,
            fileFormat="GeoTIFF",
            maxPixels=1e13,
        )
        task.start()
        print(f"[drive] started {desc} → Drive/{drive_folder}/{Path(filename).stem}.tif  (task {task.id})")
        return task

    # Local download via geemap (preferred) or ee download URL helper.
    try:
        import geemap
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Local GEE export requires geemap. Install geemap or set GEE_EXPORT_MODE=drive."
        ) from exc

    if out_path.exists():
        out_path.unlink()

    print(f"[local] exporting {filename} → {out_path} (scale={scale}m, crs={crs})")
    geemap.ee_export_image(
        image,
        filename=str(out_path),
        scale=float(scale),
        crs=crs,
        region=region,
        file_per_band=False,
    )
    if not out_path.exists():
        raise FileNotFoundError(f"Local export finished but file missing: {out_path}")
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"[local] wrote {out_path} ({size_mb:.2f} MB)")
    return out_path
