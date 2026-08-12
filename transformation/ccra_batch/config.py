"""Batch JSON models and loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_STAGES = ("extract", "compute", "acs", "risk", "publish")
DEFAULT_HAZARDS = ("flood", "heat", "landslide")
VALID_STAGES = set(DEFAULT_STAGES)
VALID_HAZARDS = set(DEFAULT_HAZARDS)


@dataclass(frozen=True)
class CitySpec:
    """One city entry from the batch JSON (pre-resolution)."""

    raw_index: int
    id: str | None = None
    slug: str | None = None
    name: str | None = None
    lat: float | None = None
    lon: float | None = None
    stages: tuple[str, ...] | None = None
    hazards: tuple[str, ...] | None = None

    def label(self) -> str:
        return self.slug or self.id or self.name or f"city[{self.raw_index}]"


@dataclass
class BatchOptions:
    continue_on_error: bool = True
    max_workers: int = 2
    skip_existing: bool = False
    upload: bool = False
    write_catalog: bool = False
    prepare_regional_cache: bool = True
    fetch_regional_layers: bool = True
    regional_sources: tuple[str, ...] = ("gfplain", "jrc", "aqueduct")
    materialize_from_regional: bool = True


@dataclass
class BatchConfig:
    batch_id: str
    region: str | None
    stages: tuple[str, ...]
    hazards: tuple[str, ...]
    options: BatchOptions
    cities: list[CitySpec]
    source_path: Path | None = None

    @property
    def n_cities(self) -> int:
        return len(self.cities)


def _as_str_tuple(value: Any, *, valid: set[str], field_name: str) -> tuple[str, ...]:
    if value is None:
        return tuple()
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty array when provided")
    out: list[str] = []
    for item in value:
        s = str(item).strip().lower()
        if s not in valid:
            raise ValueError(f"Invalid {field_name} value: {item!r}. Expected one of {sorted(valid)}")
        if s not in out:
            out.append(s)
    return tuple(out)


def _parse_city(raw: dict[str, Any], index: int) -> CitySpec:
    if not isinstance(raw, dict):
        raise ValueError(f"cities[{index}] must be an object")
    coords = raw.get("coordinates") or {}
    lat = lon = None
    if coords:
        if not isinstance(coords, dict) or "lat" not in coords or "lon" not in coords:
            raise ValueError(f"cities[{index}].coordinates requires lat and lon")
        lat = float(coords["lat"])
        lon = float(coords["lon"])
    stages = _as_str_tuple(raw.get("stages"), valid=VALID_STAGES, field_name=f"cities[{index}].stages") or None
    hazards = _as_str_tuple(raw.get("hazards"), valid=VALID_HAZARDS, field_name=f"cities[{index}].hazards") or None
    slug = raw.get("slug")
    cid = raw.get("id")
    name = raw.get("name")
    if not any([slug, cid, name, lat is not None]):
        raise ValueError(
            f"cities[{index}] needs at least one of: slug, id, name, coordinates"
        )
    return CitySpec(
        raw_index=index,
        id=str(cid).strip() if cid else None,
        slug=str(slug).strip() if slug else None,
        name=str(name).strip() if name else None,
        lat=lat,
        lon=lon,
        stages=stages,
        hazards=hazards,
    )


def load_batch_config(path: Path | str) -> BatchConfig:
    """Load and lightly validate a CCRA batch JSON file."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Batch JSON root must be an object")
    cities_raw = data.get("cities")
    if not isinstance(cities_raw, list) or not cities_raw:
        raise ValueError("'cities' must be a non-empty array")

    stages = _as_str_tuple(data.get("stages"), valid=VALID_STAGES, field_name="stages") or DEFAULT_STAGES
    hazards = _as_str_tuple(data.get("hazards"), valid=VALID_HAZARDS, field_name="hazards") or DEFAULT_HAZARDS

    opt_raw = data.get("options") or {}
    if not isinstance(opt_raw, dict):
        raise ValueError("'options' must be an object")
    options = BatchOptions(
        continue_on_error=bool(opt_raw.get("continue_on_error", True)),
        max_workers=max(1, int(opt_raw.get("max_workers", 2))),
        skip_existing=bool(opt_raw.get("skip_existing", False)),
        upload=bool(opt_raw.get("upload", False)),
        write_catalog=bool(opt_raw.get("write_catalog", False)),
        prepare_regional_cache=bool(opt_raw.get("prepare_regional_cache", True)),
        fetch_regional_layers=bool(opt_raw.get("fetch_regional_layers", True)),
        regional_sources=tuple(
            str(s).strip().lower()
            for s in (opt_raw.get("regional_sources") or ["gfplain", "jrc", "aqueduct"])
            if str(s).strip()
        ),
        materialize_from_regional=bool(opt_raw.get("materialize_from_regional", True)),
    )

    cities = [_parse_city(item, i) for i, item in enumerate(cities_raw)]
    batch_id = str(data.get("batch_id") or path.stem).strip()
    region = data.get("region")
    region_s = str(region).strip() if region else None

    return BatchConfig(
        batch_id=batch_id,
        region=region_s,
        stages=stages,
        hazards=hazards,
        options=options,
        cities=cities,
        source_path=path,
    )
