#!/usr/bin/env python3
"""Deprecated — use ``transformation/nbs_screening/flood/batch_mn_mechanism.py``."""

from __future__ import annotations

import sys

from _redirect import exec_flood_script

if __name__ == "__main__":
    argv = list(sys.argv[1:])
    if not any(
        arg == flag or arg.startswith(f"{flag}=")
        for arg in argv
        for flag in ("--sites", "--site", "--country", "--all-configured", "--exclude")
    ):
        argv = ["--country", "United States", *argv]
    sys.argv = [sys.argv[0], *argv]
    exec_flood_script("batch_mn_mechanism.py")
