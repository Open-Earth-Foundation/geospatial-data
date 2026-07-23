"""Load per-city heat_hazard site configs for score and input notebooks."""

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


def find_heat_hazard_root(start: Path | None = None) -> Path:
    """Find `transformation/heat_hazard` from a notebook working directory."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "config" / "sites").is_dir() and (candidate / "site_config.py").is_file():
            return candidate
        sibling = candidate / "heat_hazard"
        if (sibling / "config" / "sites").is_dir() and (sibling / "site_config.py").is_file():
            return sibling
        nested = candidate / "transformation" / "heat_hazard"
        if (nested / "config" / "sites").is_dir() and (nested / "site_config.py").is_file():
            return nested
    raise FileNotFoundError(
        "Could not locate transformation/heat_hazard (expected config/sites/ + site_config.py)."
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        text = f.read()
    data = yaml.safe_load(text) if yaml is not None else _minimal_yaml_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_site_config(site_slug: str | None = None, root: Path | None = None) -> dict[str, Any]:
    """Load a city site config and attach absolute path helpers used by notebooks."""
    heat_hazard_root = Path(root or find_heat_hazard_root()).resolve()
    slug = (
        site_slug
        or os.environ.get("HEAT_SITE")
        or os.environ.get("FLOODS_SITE", "porto_alegre")
    )
    config_path = heat_hazard_root / "config" / "sites" / f"{slug}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing heat_hazard site config: {config_path}")

    config = _load_yaml(config_path)
    config["heat_hazard_root"] = heat_hazard_root
    # Backward-compatible aliases used by older notebook cells.
    config["heat_root"] = heat_hazard_root
    config["config_path"] = config_path
    config["paths_abs"] = {
        key: heat_hazard_root / rel_path for key, rel_path in config.get("paths", {}).items()
    }
    config["boundary_path_abs"] = heat_hazard_root / config["boundary_path"]
    return config


def configured_path(config: dict[str, Any], path_key: str, *parts: str) -> Path:
    """Resolve a file path below a configured site or shared directory."""
    base = config["paths_abs"][path_key]
    return base.joinpath(*parts)
