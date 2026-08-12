"""CCRA multi-city batch orchestration.

Accepts a JSON batch of cities and runs the existing single-city CCRA CLIs
(extract → compute → ACS → risk → publish) with parallel workers and
partial-failure handling.

See ``docs/ccra_batch_pipeline.md`` and ``docs/examples/``.
"""

from __future__ import annotations

from .config import (
    DEFAULT_HAZARDS,
    DEFAULT_STAGES,
    BatchConfig,
    CitySpec,
    load_batch_config,
)
from .regional_cache import prepare_regional_cache
from .regional_layers import fetch_regional_flood_layers, materialize_sites_from_regional
from .resolve import list_configured_slugs, resolve_city
from .runner import run_batch

__all__ = [
    "DEFAULT_HAZARDS",
    "DEFAULT_STAGES",
    "CitySpec",
    "BatchConfig",
    "load_batch_config",
    "list_configured_slugs",
    "resolve_city",
    "prepare_regional_cache",
    "fetch_regional_flood_layers",
    "materialize_sites_from_regional",
    "run_batch",
]
