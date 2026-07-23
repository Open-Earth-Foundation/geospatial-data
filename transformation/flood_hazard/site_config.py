"""Load per-city flood_hazard site configs for score and input notebooks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - used interactively from notebooks.
    yaml = None


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        items = [item.strip() for item in value[1:-1].split(",") if item.strip()]
        return [_parse_scalar(item) for item in items]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    """Parse the small config subset used in `config/sites/*.yaml`."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, sep, value = raw_line.strip().partition(":")
        if not sep:
            continue
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip():
            parent[key] = _parse_scalar(value)
        else:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
    return root


def find_flood_hazard_root(start: Path | None = None) -> Path:
    """Find `transformation/flood_hazard` from a notebook working directory."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "config" / "sites").is_dir() and (candidate / "site_config.py").is_file():
            return candidate
        # Allow discovery when called from sibling input transformations.
        sibling = candidate / "flood_hazard"
        if (sibling / "config" / "sites").is_dir() and (sibling / "site_config.py").is_file():
            return sibling
    raise FileNotFoundError(
        "Could not locate transformation/flood_hazard (expected config/sites/ + site_config.py)."
    )


def load_site_config(site_slug: str | None = None, root: Path | None = None) -> dict[str, Any]:
    """Load a city site config and attach absolute path helpers used by notebooks."""
    flood_hazard_root = root or find_flood_hazard_root()
    flood_hazard_root = Path(flood_hazard_root).resolve()
    slug = site_slug or os.environ.get("FLOODS_SITE", "porto_alegre")
    config_path = flood_hazard_root / "config" / "sites" / f"{slug}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing flood_hazard site config: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        text = f.read()
    config = yaml.safe_load(text) if yaml is not None else _minimal_yaml_load(text)

    config["flood_hazard_root"] = flood_hazard_root
    # Backward-compatible alias for notebooks that still expect floods_root.
    config["floods_root"] = flood_hazard_root
    config["config_path"] = config_path
    config["paths_abs"] = {
        key: flood_hazard_root / rel_path for key, rel_path in config.get("paths", {}).items()
    }
    config["boundary_path_abs"] = flood_hazard_root / config["boundary_path"]
    return config


def configured_path(config: dict[str, Any], path_key: str, *parts: str) -> Path:
    """Resolve a file path below a configured site or shared directory."""
    base = config["paths_abs"][path_key]
    return base.joinpath(*parts)
