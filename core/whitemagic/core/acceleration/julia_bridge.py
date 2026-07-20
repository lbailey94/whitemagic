"""Julia Scientific Bridge - Python to Julia via subprocess.
==========================================================
Bridges to Julia scientific computing modules for statistical memory
analysis and time-series forecasting. Julia processes are called via
subprocess with JSON stdin/stdout protocol.

Julia modules:
- memory_stats.jl - Statistical memory analysis (distributions, outliers, zones)
- self_model_forecast.jl - Holt-Winters forecasting with confidence intervals

Falls back to pure Python when Julia is not available.

Usage:
    from whitemagic.core.acceleration.julia_bridge import (
        julia_importance_distribution, julia_forecast_metric,
        julia_batch_forecast, julia_bridge_status
    )
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

_julia_bin: str | None = None
_julia_lock = threading.RLock()
_HAS_JULIA = False
_JULIA_DIR: Path | None = None


def _find_julia() -> tuple:
    """Locate Julia binary and source directory."""
    base = Path(__file__).resolve().parent.parent.parent.parent
    julia_dir = base / "whitemagic-julia" / "src"

    candidates = [
        os.environ.get("JULIA_PATH", ""),
        shutil.which("julia") or "",
        "/usr/local/bin/julia",
        str(base / ".pixi" / "envs" / "default" / "bin" / "julia"),
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            if julia_dir.is_dir():
                return path, julia_dir
            return path, None
    return None, julia_dir if julia_dir.is_dir() else None


def _init_julia() -> Any:
    """Initialize Julia bridge (lazy, thread-safe)."""
    global _julia_bin, _HAS_JULIA, _JULIA_DIR
    if _julia_bin is not None or _HAS_JULIA:
        return
    with _julia_lock:
        if _julia_bin is not None or _HAS_JULIA:
            return
        _julia_bin, _JULIA_DIR = _find_julia()
        if _julia_bin and _JULIA_DIR:
            _HAS_JULIA = True
            logger.info(
                "Julia bridge initialized: bin=%s, dir=%s", _julia_bin, _JULIA_DIR
            )
        else:
            logger.debug("Julia not found - using Python fallback")


def _call_julia(module_file: str, request: dict[str, Any]) -> dict[str, Any] | None:
    """Call a Julia module via subprocess with JSON protocol."""
    _init_julia()
    if not _julia_bin or not _JULIA_DIR:
        return None

    src_path = _JULIA_DIR / module_file
    if not src_path.exists():
        logger.debug("Julia source not found: %s", src_path)
        return None

    # Build a Julia script that includes the module and processes the request
    script = f'''
using JSON3
include("{src_path}")
request = JSON3.read(readline(stdin), Dict{{String, Any}})
result = {Path(module_file).stem.title().replace("_", "")}.handle_request(request)
println(JSON3.write(result))
'''

    try:
        proc = subprocess.run(
            [_julia_bin, "-e", script],
            input=_json_dumps(request),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parsed = _json_loads(proc.stdout.strip())
            if isinstance(parsed, dict):
                return parsed
        elif proc.stderr:
            logger.debug("Julia %s stderr: %s", module_file, proc.stderr[:300])
    except subprocess.TimeoutExpired:
        logger.warning("Julia %s timed out after 60s", module_file)
    except Exception as e:  # noqa: BLE001
        logger.debug("Julia %s call failed: %s", module_file, e)

    return None


def julia_importance_distribution(
    scores: list[float],
) -> dict[str, Any] | None:
    """Analyze memory importance score distribution using Julia.

    Returns comprehensive statistics: moments, percentiles, outlier detection.
    """
    return _call_julia(
        "memory_stats.jl",
        {
            "command": "importance_distribution",
            "scores": scores,
        },
    )


def julia_zone_transitions(
    before: list[float],
    after: list[float],
) -> dict[str, Any] | None:
    """Compute galactic zone transition probabilities (Markov model).

    Args:
        before: Galactic distances before a sweep.
        after: Galactic distances after a sweep.

    """
    return _call_julia(
        "memory_stats.jl",
        {
            "command": "zone_transitions",
            "before": before,
            "after": after,
        },
    )


def julia_detect_outliers(
    values: list[float],
    threshold: float = 3.0,
) -> dict[str, Any] | None:
    """Detect outliers using modified z-score (MAD-based)."""
    return _call_julia(
        "memory_stats.jl",
        {
            "command": "detect_outliers",
            "values": values,
            "threshold": threshold,
        },
    )


def julia_cluster_significance(
    cluster_sizes: list[int],
    total_points: int,
    volume: float,
) -> dict[str, Any] | None:
    """Test cluster significance against uniform null model."""
    return _call_julia(
        "memory_stats.jl",
        {
            "command": "cluster_significance",
            "cluster_sizes": cluster_sizes,
            "total_points": total_points,
            "volume": volume,
        },
    )


def julia_full_memory_analysis(
    importance: list[float],
    distances: list[float],
) -> dict[str, Any] | None:
    """Run complete statistical analysis on memory corpus."""
    return _call_julia(
        "memory_stats.jl",
        {
            "command": "full_analysis",
            "importance": importance,
            "distances": distances,
        },
    )


def julia_forecast_metric(
    values: list[float],
    steps: int = 5,
    alpha: float = 0.3,
    beta: float = 0.1,
) -> dict[str, Any] | None:
    """Forecast a Self-Model metric using Holt-Winters exponential smoothing.

    Returns forecasts with 80% and 95% confidence intervals.
    """
    return _call_julia(
        "self_model_forecast.jl",
        {
            "command": "forecast",
            "values": values,
            "steps": steps,
            "alpha": alpha,
            "beta": beta,
        },
    )


def julia_detect_anomalies(
    values: list[float],
    threshold: float = 2.5,
) -> dict[str, Any] | None:
    """Detect anomalies in a metric time series via residual z-scores."""
    return _call_julia(
        "self_model_forecast.jl",
        {
            "command": "detect_anomalies",
            "values": values,
            "threshold": threshold,
        },
    )


def julia_metric_correlations(
    metrics: dict[str, list[float]],
) -> dict[str, Any] | None:
    """Compute pairwise Pearson correlations between Self-Model metrics."""
    return _call_julia(
        "self_model_forecast.jl",
        {
            "command": "correlations",
            "metrics": metrics,
        },
    )


def julia_batch_forecast(
    metrics: dict[str, list[float]],
    steps: int = 5,
) -> dict[str, Any] | None:
    """Forecast all Self-Model metrics in one call with alert generation."""
    return _call_julia(
        "self_model_forecast.jl",
        {
            "command": "batch_forecast",
            "metrics": metrics,
            "steps": steps,
        },
    )


def _call_julia_direct(
    module_file: str, request: dict[str, Any]
) -> dict[str, Any] | None:
    """Call a Julia module that owns its own main() JSON-stdio entry point."""
    _init_julia()
    if not _julia_bin or not _JULIA_DIR:
        return None
    src_path = _JULIA_DIR / module_file
    if not src_path.exists():
        logger.debug("Julia source not found: %s", src_path)
        return None
    try:
        proc = subprocess.run(
            [_julia_bin, "--startup-file=no", str(src_path)],
            input=_json_dumps(request),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parsed = _json_loads(proc.stdout.strip())
            if isinstance(parsed, dict):
                return parsed
        elif proc.stderr:
            logger.debug("Julia %s stderr: %s", module_file, proc.stderr[:300])
    except subprocess.TimeoutExpired:
        logger.warning("Julia %s timed out", module_file)
    except Exception as e:  # noqa: BLE001
        logger.debug("Julia %s call failed: %s", module_file, e)
    return None


def julia_rrf_fuse(
    ranked_lists: list[list[dict[str, Any]]],
    weights: list[float] | None = None,
    k: float = 60.0,
) -> list[dict[str, Any]] | None:
    """Merge N ranked memory lists via Reciprocal Rank Fusion using Julia.

    Args:
        ranked_lists: Each list is [{id, score}, ...] sorted by score desc.
        weights: Per-list weights (default: uniform 1.0).
        k: RRF constant (default 60, higher = smoother rank blending).

    Returns:
        Merged list of {id, rrf_score} sorted by score desc, or None.
    """
    res = _call_julia_direct(
        "graph_rrf.jl",
        {
            "command": "rrf_fuse",
            "lists": ranked_lists,
            "weights": weights or [1.0] * len(ranked_lists),
            "k": k,
        },
    )
    if res is None:
        return None
    if isinstance(res, list):
        return [item for item in res if isinstance(item, dict)]
    return None


def julia_pagerank(
    node_ids: list[str],
    edges: list[dict[str, Any]],
    damping: float = 0.85,
) -> list[dict[str, Any]] | None:
    """Compute PageRank scores for a memory subgraph using Julia power iteration.

    Args:
        node_ids: List of memory ID strings.
        edges: List of {source, target, weight} dicts.
        damping: Damping factor (default 0.85).

    Returns:
        List of {id, pagerank} sorted descending, or None.
    """
    res = _call_julia_direct(
        "graph_rrf.jl",
        {
            "command": "pagerank",
            "node_ids": node_ids,
            "edges": edges,
            "damping": damping,
        },
    )
    if res is None:
        return None
    if isinstance(res, list):
        return [item for item in res if isinstance(item, dict)]
    return None


def julia_score_walk_paths(
    paths: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]] | None:
    """Score BFS walk paths by weighted multi-signal product using Julia.

    Args:
        paths: List of {nodes, edge_signals, depth} dicts.
        weights: Signal weights {semantic, gravity, recency, staleness}.

    Returns:
        Paths sorted by score desc with {nodes, score, depth, terminal_id}, or None.
    """
    res = _call_julia_direct(
        "graph_rrf.jl",
        {
            "command": "score_walk_paths",
            "paths": paths,
            "weights": weights
            or {"semantic": 0.4, "gravity": 0.3, "recency": 0.2, "staleness": 0.1},
        },
    )
    if res is None:
        return None
    if isinstance(res, list):
        return [item for item in res if isinstance(item, dict)]
    return None


def julia_community_gravity(
    memory_vec: list[float],
    community_centroids: list[list[float]],
    community_ids: list[str],
) -> list[dict[str, Any]] | None:
    """Rank communities by cosine gravity toward a query vector using Julia.

    Returns:
        List of {community_id, gravity} sorted descending, or None.
    """
    res = _call_julia_direct(
        "graph_rrf.jl",
        {
            "command": "community_gravity",
            "vector": memory_vec,
            "centroids": community_centroids,
            "community_ids": community_ids,
        },
    )
    if res is None:
        return None
    if isinstance(res, list):
        return [item for item in res if isinstance(item, dict)]
    return None


def julia_bridge_status() -> dict[str, Any]:
    """Get Julia bridge status."""
    _init_julia()
    modules = {}
    if _JULIA_DIR:
        for f in [
            "memory_stats.jl",
            "self_model_forecast.jl",
            "graph_rrf.jl",
            "causal_resonance.jl",
            "constellations.jl",
            "gan_ying.jl",
        ]:
            modules[f.replace(".jl", "")] = (_JULIA_DIR / f).exists()

    return {
        "has_julia": _HAS_JULIA,
        "julia_bin": _julia_bin or "not found",
        "julia_dir": str(_JULIA_DIR) if _JULIA_DIR else "not found",
        "modules": modules,
        "backend": "julia_scientific" if _HAS_JULIA else "python_fallback",
    }


_jl = None


def _init_pyjulia() -> Any:
    """Initialize Julia runtime via PyJulia for direct spatial ops."""
    global _jl
    if _jl is not None:
        return _jl
    try:
        from julia import Main

        jl_project = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "polyglot"
            / "whitemagic-jl"
        )
        Main.eval(f'using Pkg; Pkg.activate("{jl_project}")')
        Main.eval("using WhiteMagicSpatial")
        _jl = Main
        logger.info("Julia spatial core initialized via PyJulia")
        return _jl
    except ImportError:
        logger.debug("PyJulia not installed — spatial bridge unavailable")
        return None
    except Exception as e:  # noqa: BLE001
        logger.debug("Failed to initialize PyJulia: %s", e)
        return None


def jl_batch_cosine(
    query: list[float], corpus: list[list[float]]
) -> list[float] | None:
    """Compute batch cosine similarity via Julia PyJulia."""
    jl = _init_pyjulia()
    if jl is None:
        return None
    try:
        result = jl.WhiteMagicSpatial.batch_cosine(query, corpus)
        return list(result)
    except Exception as e:  # noqa: BLE001
        logger.debug("Julia batch_cosine failed: %s", e)
        return None


def jl_spatial_status() -> dict[str, Any]:
    """Get Julia PyJulia spatial bridge status."""
    _init_pyjulia()
    return {
        "has_julia": _jl is not None,
        "backend": "julia_pyjulia" if _jl is not None else "unavailable",
        "note": "Install PyJulia and Julia to enable spatial computing bridge",
    }


def julia_cache_ks_test(x: list[float], y: list[float]) -> dict[str, Any] | None:
    """Two-sample KS test on cache access distributions.

    Compares two distributions (e.g., hit times vs miss times) to detect
    when access patterns have shifted and TTLs need re-tuning.

    Returns (d_statistic, p_value, same_distribution) or None if Julia unavailable.
    """
    return _call_julia(
        "cache_analytics.jl",
        {
            "command": "ks_test",
            "x": x,
            "y": y,
        },
    )


def julia_auto_tune_ttl(
    access_times: list[float],
    current_ttl: float = 3600.0,
) -> dict[str, Any] | None:
    """Auto-tune TTL based on access time patterns.

    Uses inter-arrival time distribution to recommend an optimal TTL
    that covers 95% of access intervals.

    Returns recommended_ttl, confidence, direction, and statistics.
    """
    return _call_julia(
        "cache_analytics.jl",
        {
            "command": "auto_tune_ttl",
            "access_times": access_times,
            "current_ttl": current_ttl,
        },
    )


def julia_cache_efficiency(
    hits: int,
    misses: int,
    evictions: int,
    expirations: int,
    size: int,
    max_size: int = 10000,
) -> dict[str, Any] | None:
    """Compute composite cache efficiency score (0-1).

    Factors: hit rate (0.5), eviction penalty (0.2), expiration penalty (0.15),
    capacity utilization (0.15).

    Returns score, individual metrics, and recommendation (healthy/monitor/tune).
    """
    return _call_julia(
        "cache_analytics.jl",
        {
            "command": "cache_efficiency",
            "hits": hits,
            "misses": misses,
            "evictions": evictions,
            "expirations": expirations,
            "size": size,
            "max_size": max_size,
        },
    )


def julia_fit_decay_model(
    access_ages: list[float],
    hit_counts: list[int],
) -> dict[str, Any] | None:
    """Fit exponential decay model to cache hit patterns.

    Models hit_count ≈ A * exp(-λ * age) to determine the decay rate
    and optimal TTL (3 half-lives).

    Returns lambda, amplitude, half_life, r_squared, recommended_ttl.
    """
    return _call_julia(
        "cache_analytics.jl",
        {
            "command": "fit_decay",
            "access_ages": access_ages,
            "hit_counts": hit_counts,
        },
    )


def julia_recommend_ttl_adjustments(
    namespaces: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Batch TTL recommendations for multiple cache namespaces.

    Each namespace dict should have: name, hits, misses, evictions,
    expirations, size, max_size, current_ttl, and optionally access_times.

    Returns per-namespace efficiency scores, TTL tuning results, and actions.
    """
    return _call_julia(
        "cache_analytics.jl",
        {
            "command": "recommend_ttl_adjustments",
            "namespaces": namespaces,
        },
    )


def julia_detect_galaxy_drift(
    baseline_importance: list[float],
    current_importance: list[float],
    baseline_distances: list[float],
    current_distances: list[float],
) -> dict[str, Any] | None:
    """Detect distributional drift in a galaxy's memory corpus.

    Compares baseline and current distributions of importance scores and
    galactic distances to detect when a galaxy's memory population has
    significantly shifted. Uses KS test for distribution comparison and
    mean/median shift detection.

    Args:
        baseline_importance: Importance scores from a prior snapshot.
        current_importance: Importance scores from current state.
        baseline_distances: Galactic distances from a prior snapshot.
        current_distances: Galactic distances from current state.

    Returns:
        Dict with drift_detected (bool), importance_drift, distance_drift,
        severity (low/medium/high), and recommendations, or None if Julia unavailable.
    """
    return _call_julia(
        "memory_stats.jl",
        {
            "command": "detect_galaxy_drift",
            "baseline_importance": baseline_importance,
            "current_importance": current_importance,
            "baseline_distances": baseline_distances,
            "current_distances": current_distances,
        },
    )
