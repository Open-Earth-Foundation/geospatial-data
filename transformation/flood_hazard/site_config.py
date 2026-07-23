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
        # Sibling folder (e.g. cwd inside transformation/wri_aqueduct/...).
        sibling = candidate / "flood_hazard"
        if (sibling / "config" / "sites").is_dir() and (sibling / "site_config.py").is_file():
            return sibling
        # Repo root (cwd = geospatial-data/).
        nested = candidate / "transformation" / "flood_hazard"
        if (nested / "config" / "sites").is_dir() and (nested / "site_config.py").is_file():
            return nested
    raise FileNotFoundError(
        "Could not locate transformation/flood_hazard (expected config/sites/ + site_config.py)."
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


def find_repo_root(flood_hazard_root: Path) -> Path:
    """Resolve geospatial-data root from transformation/flood_hazard."""
    return Path(flood_hazard_root).resolve().parent.parent


def model_config_path(flood_hazard_root: Path | None = None) -> Path:
    root = Path(flood_hazard_root or find_flood_hazard_root()).resolve()
    return find_repo_root(root) / "models" / "flood_hazard" / "config.yaml"


def load_model_config(flood_hazard_root: Path | None = None) -> dict[str, Any]:
    """Load default flood_hazard model parameters from models/flood_hazard/config.yaml."""
    path = model_config_path(flood_hazard_root)
    if not path.exists():
        return {}
    return _load_yaml(path)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Shallow-nested merge: dict values are merged one level; scalars replaced."""
    out: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = dict(out[key])
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


def load_site_config(site_slug: str | None = None, root: Path | None = None) -> dict[str, Any]:
    """Load a city site config and attach absolute path helpers used by notebooks.

    Model defaults from ``models/flood_hazard/config.yaml`` are merged under
    ``hazard`` and ``idw``; city YAML values win on conflict.
    """
    flood_hazard_root = root or find_flood_hazard_root()
    flood_hazard_root = Path(flood_hazard_root).resolve()
    slug = site_slug or os.environ.get("FLOODS_SITE", "porto_alegre")
    config_path = flood_hazard_root / "config" / "sites" / f"{slug}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing flood_hazard site config: {config_path}")

    config = _load_yaml(config_path)
    model = load_model_config(flood_hazard_root)
    model_path = model_config_path(flood_hazard_root)

    config["hazard"] = _deep_merge(model.get("hazard", {}), config.get("hazard") or {})
    config["idw"] = _deep_merge(model.get("idw", {}), config.get("idw") or {})

    config["flood_hazard_root"] = flood_hazard_root
    # Backward-compatible alias for notebooks that still expect floods_root.
    config["floods_root"] = flood_hazard_root
    config["config_path"] = config_path
    config["model_config_path"] = model_path
    config["model_config"] = model
    config["paths_abs"] = {
        key: flood_hazard_root / rel_path for key, rel_path in config.get("paths", {}).items()
    }
    config["boundary_path_abs"] = flood_hazard_root / config["boundary_path"]
    return config


def configured_path(config: dict[str, Any], path_key: str, *parts: str) -> Path:
    """Resolve a file path below a configured site or shared directory."""
    base = config["paths_abs"][path_key]
    return base.joinpath(*parts)
