"""Stage command builders for the single-city CCRA CLIs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .resolve import repo_root


@dataclass(frozen=True)
class StageCommand:
    stage: str  # extract|compute|acs|risk|publish
    hazard: str | None  # flood|heat|landslide|None for acs
    label: str
    argv: tuple[str, ...]
    output_marker: Path | None = None
    # If set, any existing path matching this glob (relative to repo root or absolute) counts as done.
    output_glob: str | None = None


def _py() -> str:
    root = repo_root()
    venv_py = root / ".venv" / "bin" / "python"
    return str(venv_py) if venv_py.is_file() else "python"


def build_city_commands(
    slug: str,
    *,
    stages: tuple[str, ...],
    hazards: tuple[str, ...],
    upload: bool = False,
    write_catalog: bool = False,
    regional_cache_dir: str | None = None,
) -> list[StageCommand]:
    """Return ordered subprocess argv specs for one city."""
    root = repo_root()
    py = _py()
    cmds: list[StageCommand] = []

    hazard_mods = {
        "flood": "flood_hazard",
        "heat": "heat_hazard",
        "landslide": "landslide_hazard",
    }
    risk_mods = {
        "flood": "flood_risk",
        "heat": "heat_risk",
        "landslide": "landslide_risk",
    }

    if "extract" in stages:
        for hz in hazards:
            mod = hazard_mods[hz]
            script = root / "transformation" / mod / f"extract_{hz}_inputs.py"
            marker = root / "transformation" / mod / "sites" / slug / "data" / "input"
            argv = [py, str(script), "--site", slug]
            if hz == "flood" and regional_cache_dir:
                argv.extend(["--regional-cache", regional_cache_dir])
            cmds.append(
                StageCommand(
                    stage="extract",
                    hazard=hz,
                    label=f"{slug}/{hz}/extract",
                    argv=tuple(argv),
                    output_marker=marker,
                    output_glob=str(marker / "*.tif"),
                )
            )

    if "compute" in stages:
        for hz in hazards:
            mod = hazard_mods[hz]
            script = root / "transformation" / mod / f"compute_{hz}_hazard.py"
            out_dir = root / "transformation" / mod / "sites" / slug / "data" / "output"
            # Landslide scores are named *_90m.tif; flood/heat use exact slug suffix.
            cmds.append(
                StageCommand(
                    stage="compute",
                    hazard=hz,
                    label=f"{slug}/{hz}/compute",
                    argv=(py, str(script), "--site", slug),
                    output_marker=out_dir / f"{hz}_hazard_score_{slug}.tif",
                    output_glob=str(out_dir / f"{hz}_hazard_score_{slug}*.tif"),
                )
            )

    if "acs" in stages:
        script = root / "transformation" / "acs_ev" / "extract_acs_ev.py"
        marker = (
            root
            / "transformation"
            / "acs_ev"
            / "sites"
            / slug
            / "data"
            / "output"
            / "acs_ev_block_groups.gpkg"
        )
        cmds.append(
            StageCommand(
                stage="acs",
                hazard=None,
                label=f"{slug}/acs",
                argv=(py, str(script), "--site", slug),
                output_marker=marker,
            )
        )

    if "risk" in stages:
        for hz in hazards:
            mod = risk_mods[hz]
            script = root / "transformation" / mod / f"compute_{hz}_risk.py"
            out_dir = root / "transformation" / mod / "sites" / slug / "data" / "output"
            cmds.append(
                StageCommand(
                    stage="risk",
                    hazard=hz,
                    label=f"{slug}/{hz}/risk",
                    argv=(py, str(script), "--site", slug),
                    output_marker=out_dir / f"{hz}_risk_score_{slug}.tif",
                    output_glob=str(out_dir / f"{hz}_risk_score_{slug}*.tif"),
                )
            )

    if "publish" in stages:
        publish_specs: list[tuple[str, str, str | None]] = []
        for hz in hazards:
            publish_specs.append((hazard_mods[hz], f"{hz}_hazard_publish.py", hz))
        for hz in hazards:
            publish_specs.append((risk_mods[hz], f"{hz}_risk_publish.py", hz))

        for mod, script_name, hz in publish_specs:
            script = root / "transformation" / mod / script_name
            argv = [py, str(script), "--site", slug]
            if upload:
                argv.append("--upload")
            if write_catalog:
                argv.append("--write-catalog")
            out_dir = root / "transformation" / mod / "sites" / slug / "out"
            cmds.append(
                StageCommand(
                    stage="publish",
                    hazard=hz,
                    label=f"{slug}/{hz}/publish:{script_name}",
                    argv=tuple(argv),
                    output_marker=out_dir,
                    output_glob=str(out_dir / "**" / "*"),
                )
            )

    return cmds


def should_skip(cmd: StageCommand, *, skip_existing: bool) -> bool:
    """Return True when skip_existing and primary outputs already exist."""
    if not skip_existing:
        return False

    if cmd.output_glob:
        pattern = Path(cmd.output_glob)
        parent = pattern.parent
        name = pattern.name
        if name == "*" and parent.name == "**":
            out_root = parent.parent
            if out_root.is_dir() and any(p.is_file() for p in out_root.rglob("*")):
                return True
        elif parent.is_dir() and any(parent.glob(name)):
            return True

    marker = cmd.output_marker
    if marker is None:
        return False
    if marker.is_file():
        return True
    if marker.is_dir() and any(p.is_file() for p in marker.rglob("*")):
        return True
    return False
