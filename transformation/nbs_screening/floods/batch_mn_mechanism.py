#!/usr/bin/env python3
"""Backward-compatible entry point — prefer ``floods/batch_mechanism.py``.

Defaults to United States configured sites (current Minnesota cohort).
"""

from __future__ import annotations

import sys

from batch_mechanism import main

if __name__ == "__main__":
    argv = list(sys.argv[1:])
    if not any(
        arg == flag or arg.startswith(f"{flag}=")
        for arg in argv
        for flag in ("--sites", "--site", "--country", "--all-configured", "--exclude")
    ):
        argv = ["--country", "United States", *argv]
    raise SystemExit(main(argv))
