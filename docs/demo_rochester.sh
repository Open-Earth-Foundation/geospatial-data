#!/usr/bin/env bash
# CCRA demo script — Rochester, MN
#
# Usage:
#   ./docs/demo_rochester.sh print           # print commands only (meeting talk track)
#   ./docs/demo_rochester.sh run             # execute full pipeline (long: GEE extracts)
#   ./docs/demo_rochester.sh run compute     # skip extracts; compute hazards + ACS + risk
#   ./docs/demo_rochester.sh run publish     # local COG/tiles only (no S3)
#   ./docs/demo_rochester.sh run upload      # publish + S3 + catalog (intentional)
#
# Prereqs:
#   cd geospatial-data && source .venv/bin/activate
#   earthengine authenticate   # once
#   export CENSUS_API_KEY=...  # for ACS
#   optional: export EE_PROJECT=eecc-maureen
#   optional: SITE=rochester   # default

set -euo pipefail

SITE="${SITE:-rochester}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${1:-print}"   # print | run
PHASE="${2:-all}"    # all | compute | publish | upload | flood | heat | landslide | acs | risk | hazards

if [[ "$MODE" != "print" && "$MODE" != "run" ]]; then
  echo "Usage: $0 print|run [all|compute|publish|upload|hazards|risk|acs|flood|heat|landslide]" >&2
  exit 2
fi

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="${PYTHON:-$ROOT/.venv/bin/python}"
else
  PY="${PYTHON:-python}"
fi

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
hint() { echo "    QA open: $1"; }

run_cmd() {
  echo "+ $*"
  if [[ "$MODE" == "run" ]]; then
    "$@"
  fi
}

do_extracts() {
  [[ "$PHASE" == "all" || "$PHASE" == "hazards" || "$PHASE" == "flood" || "$PHASE" == "heat" || "$PHASE" == "landslide" ]]
}

do_compute_hazard() {
  [[ "$PHASE" == "all" || "$PHASE" == "compute" || "$PHASE" == "hazards" || "$PHASE" == "flood" || "$PHASE" == "heat" || "$PHASE" == "landslide" ]]
}

do_acs() {
  [[ "$PHASE" == "all" || "$PHASE" == "compute" || "$PHASE" == "acs" ]]
}

do_risk() {
  [[ "$PHASE" == "all" || "$PHASE" == "compute" || "$PHASE" == "risk" ]]
}

do_publish() {
  [[ "$PHASE" == "all" || "$PHASE" == "publish" || "$PHASE" == "upload" ]]
}

say "CCRA pipeline demo — site=${SITE}  mode=${MODE}  phase=${PHASE}"
echo "Repo: $ROOT"
echo "Python: $PY"

# ── 0) Setup ──────────────────────────────────────────────────────────────
say "0) Setup (once per shell)"
echo "+ cd $ROOT && source .venv/bin/activate"
echo "+ export CENSUS_API_KEY=…     # required for ACS extract"
echo "+ # optional: export EE_PROJECT=eecc-maureen"

# ── 1–3) Hazards: extract ─────────────────────────────────────────────────
if do_extracts; then
  if [[ "$PHASE" == "all" || "$PHASE" == "hazards" || "$PHASE" == "flood" ]]; then
    say "1) Flood hazard — extract inputs (+ SVG QA)"
    run_cmd "$PY" transformation/flood_hazard/extract_flood_inputs.py --site "$SITE"
    hint "transformation/flood_hazard/sites/${SITE}/data/intermediate/qa_inputs/"
  fi
  if [[ "$PHASE" == "all" || "$PHASE" == "hazards" || "$PHASE" == "heat" ]]; then
    say "2) Heat hazard — extract inputs (+ SVG QA)"
    run_cmd "$PY" transformation/heat_hazard/extract_heat_inputs.py --site "$SITE"
    hint "transformation/heat_hazard/sites/${SITE}/data/intermediate/qa_inputs/"
  fi
  if [[ "$PHASE" == "all" || "$PHASE" == "hazards" || "$PHASE" == "landslide" ]]; then
    say "3) Landslide hazard — extract inputs (+ SVG QA)"
    run_cmd "$PY" transformation/landslide_hazard/extract_landslide_inputs.py --site "$SITE"
    hint "transformation/landslide_hazard/sites/${SITE}/data/intermediate/qa_inputs/"
  fi
fi

# ── 1–3) Hazards: compute ─────────────────────────────────────────────────
if do_compute_hazard; then
  if [[ "$PHASE" == "all" || "$PHASE" == "compute" || "$PHASE" == "hazards" || "$PHASE" == "flood" ]]; then
    say "1b) Flood hazard — compute score + IDW + SVG QA"
    run_cmd "$PY" transformation/flood_hazard/compute_flood_hazard.py --site "$SITE"
    hint "transformation/flood_hazard/sites/${SITE}/data/output/map_flood_hazard_score_idw.svg"
  fi
  if [[ "$PHASE" == "all" || "$PHASE" == "compute" || "$PHASE" == "hazards" || "$PHASE" == "heat" ]]; then
    say "2b) Heat hazard — compute"
    run_cmd "$PY" transformation/heat_hazard/compute_heat_hazard.py --site "$SITE"
    hint "transformation/heat_hazard/sites/${SITE}/data/output/map_heat_hazard_score.svg"
  fi
  if [[ "$PHASE" == "all" || "$PHASE" == "compute" || "$PHASE" == "hazards" || "$PHASE" == "landslide" ]]; then
    say "3b) Landslide hazard — compute"
    run_cmd "$PY" transformation/landslide_hazard/compute_landslide_hazard.py --site "$SITE"
    hint "transformation/landslide_hazard/sites/${SITE}/data/output/map_landslide_hazard_score.svg"
  fi
fi

# ── 4) ACS E/V ─────────────────────────────────────────────────────────────
if do_acs; then
  say "4) ACS exposure & vulnerability (shared E/V)"
  if [[ "$MODE" == "run" && -z "${CENSUS_API_KEY:-}" ]]; then
    echo "ERROR: export CENSUS_API_KEY=... before ACS extract" >&2
    exit 1
  fi
  run_cmd "$PY" transformation/acs_ev/extract_acs_ev.py --site "$SITE"
  hint "transformation/acs_ev/sites/${SITE}/data/output/map_exposure_population_density.svg"
  hint "transformation/acs_ev/sites/${SITE}/data/output/map_vulnerability_composite.svg"
fi

# ── 5) Risk ────────────────────────────────────────────────────────────────
if do_risk; then
  say "5) Risk R = (H × E × V)^(1/3) — flood / heat / landslide"
  run_cmd "$PY" transformation/flood_risk/compute_flood_risk.py --site "$SITE"
  hint "transformation/flood_risk/sites/${SITE}/data/output/map_flood_risk_score_grid.svg"

  run_cmd "$PY" transformation/heat_risk/compute_heat_risk.py --site "$SITE"
  hint "transformation/heat_risk/sites/${SITE}/data/output/map_heat_risk_score_grid.svg"

  run_cmd "$PY" transformation/landslide_risk/compute_landslide_risk.py --site "$SITE"
  hint "transformation/landslide_risk/sites/${SITE}/data/output/map_landslide_risk_score_grid.svg"
fi

# ── 6) Publish ─────────────────────────────────────────────────────────────
if do_publish; then
  if [[ "$PHASE" == "upload" ]]; then
    say "6) Publish — COG + tiles + S3 + catalog"
    pub() { run_cmd "$PY" "$@" --upload --write-catalog; }
  else
    say "6) Publish — build COG + tiles locally (dry-run catalog unless --upload)"
    pub() { run_cmd "$PY" "$@"; }
  fi

  pub transformation/flood_hazard/flood_hazard_publish.py --site "$SITE" --build
  pub transformation/heat_hazard/heat_hazard_publish.py --site "$SITE" --build
  pub transformation/landslide_hazard/landslide_hazard_publish.py --site "$SITE" --build

  pub transformation/flood_risk/flood_risk_publish.py --site "$SITE" --product risk --build
  pub transformation/heat_risk/heat_risk_publish.py --site "$SITE" --product risk --build
  pub transformation/landslide_risk/landslide_risk_publish.py --site "$SITE" --product risk --build
fi

# ── Meeting shortcuts ──────────────────────────────────────────────────────
say "Meeting shortcuts"
cat <<EOF
# Talk track (print all commands, do not execute):
  ./docs/demo_rochester.sh print

# Live short path (inputs already extracted):
  export CENSUS_API_KEY=…
  ./docs/demo_rochester.sh run compute

# Full city run (long — Earth Engine extracts):
  ./docs/demo_rochester.sh run

# Publish local only:
  ./docs/demo_rochester.sh run publish

# Publish + S3 + catalog (intentional):
  ./docs/demo_rochester.sh run upload

# One-liners:
  $PY transformation/flood_hazard/compute_flood_hazard.py --site rochester
  $PY transformation/flood_risk/compute_flood_risk.py --site rochester
  $PY transformation/flood_risk/flood_risk_publish.py --site rochester --product risk --build
EOF

say "Done (mode=${MODE}). Architecture: docs/ccra_pipeline_architecture.md"
