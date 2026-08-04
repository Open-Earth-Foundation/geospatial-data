"""Deprecated ``floods/`` → ``flood/`` shim (N10a; remove after one release)."""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path


def exec_flood_script(script_name: str) -> None:
    warnings.warn(
        "transformation/nbs_screening/floods/ is deprecated; use flood/ instead.",
        DeprecationWarning,
        stacklevel=3,
    )
    target = Path(__file__).resolve().parent.parent / "flood" / script_name
    os.execv(sys.executable, [sys.executable, str(target), *sys.argv[1:]])
