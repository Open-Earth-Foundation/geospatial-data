"""Unit tests for CCRA batch JSON load + city resolution (no GEE)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "transformation"))

from ccra_batch.config import load_batch_config  # noqa: E402
from ccra_batch.resolve import list_configured_slugs, resolve_city  # noqa: E402
from ccra_batch.runner import run_batch  # noqa: E402
from ccra_batch.stages import build_city_commands  # noqa: E402


class CcraBatchTests(unittest.TestCase):
    def test_list_configured_includes_minnesota_cities(self) -> None:
        slugs = set(list_configured_slugs())
        for needed in ("plymouth", "edina", "richfield", "apple_valley", "rochester"):
            self.assertIn(needed, slugs)

    def test_load_minnesota_example(self) -> None:
        path = ROOT / "docs" / "examples" / "ccra_batch_minnesota.json"
        cfg = load_batch_config(path)
        self.assertEqual(cfg.n_cities, 5)
        self.assertEqual(cfg.region, "minnesota")
        self.assertTrue(cfg.options.continue_on_error)

    def test_resolve_by_slug_name_coords(self) -> None:
        path = ROOT / "docs" / "examples" / "ccra_batch_resolve_demo.json"
        cfg = load_batch_config(path)
        resolved = [
            resolve_city(c, default_stages=cfg.stages, default_hazards=cfg.hazards)
            for c in cfg.cities
        ]
        slugs = [r.slug for r in resolved]
        self.assertEqual(
            slugs,
            ["plymouth", "edina", "richfield", "apple_valley", "rochester"],
        )

    def test_build_commands_shape(self) -> None:
        cmds = build_city_commands(
            "rochester",
            stages=("compute", "acs", "risk"),
            hazards=("flood", "heat"),
        )
        labels = [c.label for c in cmds]
        self.assertIn("rochester/flood/compute", labels)
        self.assertIn("rochester/acs", labels)
        self.assertIn("rochester/heat/risk", labels)
        self.assertTrue(all(c.argv[2] == "--site" and c.argv[3] == "rochester" for c in cmds))

    def test_clip_regional_to_city_bbox(self) -> None:
        import numpy as np
        import rasterio
        from rasterio.transform import from_bounds

        from ccra_batch.clip_to_site import clip_raster_to_site

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Regional grid covering Twin Cities-ish bbox
            west, south, east, north = -94.0, 44.5, -92.0, 45.2
            width, height = 200, 70
            transform = from_bounds(west, south, east, north, width, height)
            regional = tmp_path / "gfplain_250m.tif"
            data = np.arange(height * width, dtype=np.float32).reshape(height, width)
            profile = {
                "driver": "GTiff",
                "height": height,
                "width": width,
                "count": 1,
                "dtype": "float32",
                "crs": "EPSG:4326",
                "transform": transform,
                "compress": "deflate",
            }
            with rasterio.open(regional, "w", **profile) as dst:
                dst.write(data, 1)

            out = tmp_path / "gfplain_plymouth.tif"
            # Plymouth-ish bbox inside regional
            clip_raster_to_site(
                regional,
                out,
                bbox=[-93.522652, 44.978282, -93.400372, 45.066422],
            )
            self.assertTrue(out.is_file())
            with rasterio.open(out) as src:
                self.assertGreater(src.width, 0)
                self.assertGreater(src.height, 0)
                self.assertLess(src.width, width)
                self.assertLess(src.height, height)

    def test_flood_extract_argv_includes_regional_cache(self) -> None:
        cmds = build_city_commands(
            "rochester",
            stages=("extract",),
            hazards=("flood",),
            regional_cache_dir="/tmp/fake-cache",
        )
        self.assertEqual(len(cmds), 1)
        argv = cmds[0].argv
        self.assertIn("--regional-cache", argv)
        self.assertIn("/tmp/fake-cache", argv)

    def test_dry_run_batch_five_cities_parallel(self) -> None:
        path = ROOT / "docs" / "examples" / "ccra_batch_minnesota.json"
        cfg = load_batch_config(path)
        cfg.stages = ("compute", "acs", "risk")
        result = run_batch(cfg, dry_run=True, max_workers=4, continue_on_error=True)
        self.assertTrue(result.ok)
        self.assertEqual(len(result.cities), 5)
        self.assertTrue(result.regional_cache_dir)
        self.assertTrue(Path(result.regional_cache_dir).joinpath("manifest.json").is_file())

    def test_partial_failure_on_unknown_city(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(
                json.dumps(
                    {
                        "batch_id": "partial",
                        "region": "minnesota",
                        "options": {"continue_on_error": True, "max_workers": 1},
                        "cities": [
                            {"slug": "plymouth"},
                            {"slug": "not_a_real_city"},
                            {"slug": "edina"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            cfg = load_batch_config(path)
            result = run_batch(cfg, dry_run=True, continue_on_error=True)
            self.assertFalse(result.ok)
            statuses = {c.slug: c.status for c in result.cities}
            self.assertEqual(statuses.get("plymouth"), "ok")
            self.assertEqual(statuses.get("edina"), "ok")
            self.assertEqual(statuses.get("not_a_real_city"), "failed")


if __name__ == "__main__":
    unittest.main()
