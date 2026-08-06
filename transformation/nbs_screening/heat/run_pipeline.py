#!/usr/bin/env python3
"""End-to-end heat NBS pipeline orchestrator (H4).

Per configured city:

  1. Mechanism input layers extract — optional
  2. Heat mechanism grid compute (+ QA SVG)
  3. COG/tiles publish — optional

Example:
  python transformation/nbs_screening/heat/run_pipeline.py --site richfield
  python transformation/nbs_screening/heat/run_pipeline.py \\
    --country "United States" --skip-inputs
  python transformation/nbs_screening/heat/run_pipeline.py \\
    --site richfield --skip-publish
"""

from __future__ import annotations

from batch_mechanism import main

if __name__ == "__main__":
    raise SystemExit(main())
