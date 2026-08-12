"""Execute multi-city CCRA batches with parallelism and partial failure."""

from __future__ import annotations

import json
import os
import subprocess
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .config import BatchConfig
from .regional_cache import prepare_regional_cache
from .regional_layers import fetch_regional_flood_layers, materialize_sites_from_regional
from .resolve import ResolvedCity, resolve_city
from .stages import StageCommand, build_city_commands, should_skip

StepStatus = Literal["ok", "skipped", "failed", "pending"]


@dataclass
class StepResult:
    label: str
    stage: str
    hazard: str | None
    status: StepStatus
    seconds: float = 0.0
    returncode: int | None = None
    error: str | None = None


@dataclass
class CityResult:
    slug: str
    request_label: str
    resolution: str
    display_name: str
    status: StepStatus
    seconds: float = 0.0
    steps: list[StepResult] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in {"ok", "skipped"} and self.error is None


@dataclass
class BatchResult:
    batch_id: str
    region: str | None
    cities: list[CityResult]
    started_at: str
    finished_at: str
    wall_seconds: float
    sequential_estimate_seconds: float
    regional_cache_dir: str | None = None
    dry_run: bool = False

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.cities)

    def efficiency_ratio(self) -> float | None:
        """wall / sum(per-city). <1 means parallel speedup vs sequential estimate."""
        if self.sequential_estimate_seconds <= 0:
            return None
        return self.wall_seconds / self.sequential_estimate_seconds


def _run_stage(cmd: StageCommand, *, dry_run: bool, skip_existing: bool) -> StepResult:
    if should_skip(cmd, skip_existing=skip_existing):
        return StepResult(
            label=cmd.label,
            stage=cmd.stage,
            hazard=cmd.hazard,
            status="skipped",
            seconds=0.0,
        )
    if dry_run:
        return StepResult(
            label=cmd.label,
            stage=cmd.stage,
            hazard=cmd.hazard,
            status="ok",
            seconds=0.0,
        )

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            list(cmd.argv),
            check=False,
            capture_output=True,
            text=True,
        )
        seconds = time.perf_counter() - t0
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            if len(err) > 2000:
                err = err[-2000:]
            return StepResult(
                label=cmd.label,
                stage=cmd.stage,
                hazard=cmd.hazard,
                status="failed",
                seconds=seconds,
                returncode=proc.returncode,
                error=err or f"exit {proc.returncode}",
            )
        return StepResult(
            label=cmd.label,
            stage=cmd.stage,
            hazard=cmd.hazard,
            status="ok",
            seconds=seconds,
            returncode=0,
        )
    except Exception as exc:  # noqa: BLE001
        return StepResult(
            label=cmd.label,
            stage=cmd.stage,
            hazard=cmd.hazard,
            status="failed",
            seconds=time.perf_counter() - t0,
            error=str(exc),
        )


def _run_one_city(
    city: ResolvedCity,
    *,
    upload: bool,
    write_catalog: bool,
    skip_existing: bool,
    dry_run: bool,
    regional_cache_dir: str | None = None,
) -> CityResult:
    t0 = time.perf_counter()
    result = CityResult(
        slug=city.slug,
        request_label=city.request_label,
        resolution=city.resolution,
        display_name=city.display_name,
        status="pending",
    )
    # Prefer regional flood layers when the batch prepared them.
    if regional_cache_dir:
        os.environ["CCRA_REGIONAL_CACHE"] = regional_cache_dir
    try:
        cmds = build_city_commands(
            city.slug,
            stages=city.stages,
            hazards=city.hazards,
            upload=upload,
            write_catalog=write_catalog,
            regional_cache_dir=regional_cache_dir,
        )
        for cmd in cmds:
            step = _run_stage(cmd, dry_run=dry_run, skip_existing=skip_existing)
            result.steps.append(step)
            if step.status == "failed":
                result.status = "failed"
                result.error = f"{step.label}: {step.error}"
                break
        else:
            if result.steps and all(s.status == "skipped" for s in result.steps):
                result.status = "skipped"
            else:
                result.status = "ok"
    except Exception as exc:  # noqa: BLE001
        result.status = "failed"
        result.error = str(exc)
        result.steps.append(
            StepResult(
                label=f"{city.slug}/pipeline",
                stage="pipeline",
                hazard=None,
                status="failed",
                error="".join(traceback.format_exception_only(type(exc), exc)).strip(),
            )
        )
    result.seconds = time.perf_counter() - t0
    return result


def _run_one_city_job(payload: dict[str, Any]) -> CityResult:
    """Worker entrypoint for thread pool."""
    city = ResolvedCity(**payload["city"])
    return _run_one_city(
        city,
        upload=payload["upload"],
        write_catalog=payload["write_catalog"],
        skip_existing=payload["skip_existing"],
        dry_run=payload["dry_run"],
        regional_cache_dir=payload.get("regional_cache_dir"),
    )


def run_batch(
    config: BatchConfig,
    *,
    dry_run: bool = False,
    max_workers: int | None = None,
    continue_on_error: bool | None = None,
) -> BatchResult:
    started = datetime.now(timezone.utc)
    t_wall0 = time.perf_counter()

    resolved: list[ResolvedCity] = []
    resolve_failures: list[CityResult] = []
    for city in config.cities:
        try:
            resolved.append(
                resolve_city(
                    city,
                    default_stages=config.stages,
                    default_hazards=config.hazards,
                )
            )
        except Exception as exc:  # noqa: BLE001
            resolve_failures.append(
                CityResult(
                    slug=city.slug or city.id or "unresolved",
                    request_label=city.label(),
                    resolution="failed",
                    display_name=city.label(),
                    status="failed",
                    error=str(exc),
                )
            )
            if not (config.options.continue_on_error if continue_on_error is None else continue_on_error):
                finished = datetime.now(timezone.utc)
                return BatchResult(
                    batch_id=config.batch_id,
                    region=config.region,
                    cities=resolve_failures,
                    started_at=started.isoformat(),
                    finished_at=finished.isoformat(),
                    wall_seconds=time.perf_counter() - t_wall0,
                    sequential_estimate_seconds=0.0,
                    dry_run=dry_run,
                )

    cache_dir = None
    if config.options.prepare_regional_cache and config.region and resolved:
        cache_dir = str(
            prepare_regional_cache(
                region=config.region,
                batch_id=config.batch_id,
                cities=resolved,
            )
        )
        # One regional GEE fetch for fixed-transform flood layers, then optional
        # pre-clip into each city input dir (city workers still run extract for GFD/QA).
        if config.options.fetch_regional_layers and not dry_run:
            try:
                fetch_regional_flood_layers(
                    Path(cache_dir),
                    sources=config.options.regional_sources,
                    skip_existing=True,
                )
                if config.options.materialize_from_regional:
                    materialize_sites_from_regional(
                        Path(cache_dir),
                        [c.slug for c in resolved],
                    )
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[regional-fetch] WARNING: {exc} — falling back to per-city GEE extracts",
                    file=__import__("sys").stderr,
                )
        elif config.options.fetch_regional_layers and dry_run:
            print(
                f"[regional-fetch] dry-run: would fetch {list(config.options.regional_sources)} "
                f"into {cache_dir}/layers/"
            )

    workers = max_workers or config.options.max_workers
    cont = config.options.continue_on_error if continue_on_error is None else continue_on_error
    city_results: list[CityResult] = list(resolve_failures)

    jobs = [
        {
            "city": asdict(city),
            "upload": config.options.upload,
            "write_catalog": config.options.write_catalog,
            "skip_existing": config.options.skip_existing,
            "dry_run": dry_run,
            "regional_cache_dir": cache_dir,
        }
        for city in resolved
    ]

    if workers <= 1 or len(jobs) <= 1:
        for job in jobs:
            result = _run_one_city_job(job)
            city_results.append(result)
            if not result.ok and not cont:
                break
    else:
        # Parallel across cities. Stages within a city stay sequential
        # (hazard extract → compute → ACS → risk depends on prior outputs).
        # Threads are appropriate because each stage shells out to a subprocess.
        with ThreadPoolExecutor(max_workers=min(workers, len(jobs))) as pool:
            futures = {pool.submit(_run_one_city_job, job): job for job in jobs}
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                except Exception as exc:  # noqa: BLE001
                    job = futures[fut]
                    slug = job["city"]["slug"]
                    result = CityResult(
                        slug=slug,
                        request_label=job["city"]["request_label"],
                        resolution=job["city"]["resolution"],
                        display_name=job["city"]["display_name"],
                        status="failed",
                        error=str(exc),
                    )
                city_results.append(result)
                if not result.ok and not cont:
                    for other in futures:
                        other.cancel()
                    break

    # Stable order by original request when possible
    order = {c.slug: i for i, c in enumerate(resolved)}
    city_results.sort(key=lambda r: order.get(r.slug, 10_000))

    wall = time.perf_counter() - t_wall0
    seq_est = sum(c.seconds for c in city_results)
    finished = datetime.now(timezone.utc)
    return BatchResult(
        batch_id=config.batch_id,
        region=config.region,
        cities=city_results,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        wall_seconds=wall,
        sequential_estimate_seconds=seq_est,
        regional_cache_dir=cache_dir,
        dry_run=dry_run,
    )


def write_batch_report(result: BatchResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "batch_id": result.batch_id,
        "region": result.region,
        "dry_run": result.dry_run,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "wall_seconds": round(result.wall_seconds, 3),
        "sequential_estimate_seconds": round(result.sequential_estimate_seconds, 3),
        "efficiency_ratio": result.efficiency_ratio(),
        "ok": result.ok,
        "regional_cache_dir": result.regional_cache_dir,
        "cities": [
            {
                "slug": c.slug,
                "request_label": c.request_label,
                "resolution": c.resolution,
                "display_name": c.display_name,
                "status": c.status,
                "seconds": round(c.seconds, 3),
                "error": c.error,
                "steps": [
                    {
                        "label": s.label,
                        "stage": s.stage,
                        "hazard": s.hazard,
                        "status": s.status,
                        "seconds": round(s.seconds, 3),
                        "returncode": s.returncode,
                        "error": s.error,
                    }
                    for s in c.steps
                ],
            }
            for c in result.cities
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def print_summary(result: BatchResult) -> None:
    print("\n=== CCRA batch summary ===")
    print(f"batch_id: {result.batch_id}")
    if result.region:
        print(f"region:   {result.region}")
    print(f"dry_run:  {result.dry_run}")
    print(f"cities:   {len(result.cities)}")
    print(f"wall_s:   {result.wall_seconds:.2f}")
    print(f"sum_city_s (sequential estimate): {result.sequential_estimate_seconds:.2f}")
    ratio = result.efficiency_ratio()
    if ratio is not None and not result.dry_run and result.sequential_estimate_seconds >= 1.0:
        print(f"efficiency_ratio (wall/sum): {ratio:.3f}  (<1 ⇒ parallel speedup)")
    elif result.dry_run:
        print("efficiency_ratio: n/a on --dry-run (use a real multi-city run to benchmark)")
    if result.regional_cache_dir:
        print(f"regional_cache: {result.regional_cache_dir}")
    print("")
    for city in result.cities:
        flag = "OK" if city.ok else "FAIL"
        print(f"  [{flag}] {city.slug:16} {city.seconds:8.2f}s  via={city.resolution}")
        if city.error:
            print(f"         error: {city.error[:300]}")
    print(f"\noverall: {'SUCCESS' if result.ok else 'PARTIAL/FAILED'}")
