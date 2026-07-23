"""Re-export shared GEE local export helper for notebooks on this package path."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SHARED = Path(__file__).resolve().parent.parent / "gee_local_export.py"
_spec = importlib.util.spec_from_file_location("_oef_gee_local_export", _SHARED)
if _spec is None or _spec.loader is None:  # pragma: no cover
    raise ImportError(f"Could not load shared helper at {_SHARED}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

export_image_to_input = _mod.export_image_to_input
export_mode = _mod.export_mode

__all__ = ["export_image_to_input", "export_mode"]
