"""Polyglot Memory Handlers — Bridge holographic memory queries to Julia/Elixir/Haskell/Rust.

Dynamically adds the polyglot bridge path to sys.path and monkey-patches
POLYGLOT_ROOT so the bridge resolves files correctly regardless of import context.
"""
# ruff: noqa: BLE001

import logging
import os
import sys
import time as _time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Compute repo root from this file's location:
# core/whitemagic/tools/handlers/polyglot.py -> 5 parents up -> WHITEMAGIC
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_POLYglot_BRIDGE = _REPO_ROOT / "polyglot" / "bridges" / "python"

# Ensure the bridge module is importable
if str(_POLYglot_BRIDGE) not in sys.path:
    sys.path.insert(0, str(_POLYglot_BRIDGE))

try:
    import whitemagic_polyglot as _wp

    _wp.POLYGLOT_ROOT = _REPO_ROOT / "polyglot"
except ImportError:
    _wp = None  # type: ignore[assignment]
    logger.warning("Polyglot bridge not importable from %s", _POLYglot_BRIDGE)


_BackendCls = type("BackendCls", (), {})
if _wp is not None:
    _BackendCls = _wp  # type: ignore[assignment]


def _resolve_backend(backend_name: str) -> Any:
    """Resolve backend name to an instantiated backend context manager."""
    if _wp is None:
        raise RuntimeError("Polyglot bridge unavailable")

    if backend_name == "auto":
        return _wp.auto()

    mapping = {
        "julia": _wp.JuliaBackend,
        "elixir": _wp.ElixirBackend,
        "haskell": _wp.HaskellBackend,
        "rust": _wp.RustBackend,
        "koka": _wp.KokaBackend,
        "rust_evolution": _wp.RustEvolutionBackend,
        "julia_yield": _wp.JuliaYieldBackend,
        "elixir_actor": _wp.ElixirActorBackend,
    }
    cls = mapping.get(backend_name)
    if cls is None:
        raise ValueError(f"Unknown backend: {backend_name}")
    return cls()


def handle_polyglot_memory_query(**kwargs: Any) -> dict[str, Any]:
    """Execute a holographic memory query through a polyglot backend."""
    operation = kwargs.get("operation")
    if not operation:
        return {"status": "error", "error": "operation is required"}

    backend_name = kwargs.get("backend", "auto")

    try:
        backend_ctx = _resolve_backend(backend_name)
    except RuntimeError as e:
        return {
            "status": "error",
            "error": str(e),
            "error_code": "polyglot_unavailable",
        }
    except ValueError as e:
        return {"status": "error", "error": str(e), "error_code": "invalid_backend"}

    with backend_ctx as backend:
        try:
            if operation == "encode":
                text = kwargs.get("text", "")
                raw = backend.call("encode", text=text)
                result = raw.get("result", raw) if raw.get("status") == "ok" else raw
                return {"status": "success", "operation": "encode", "result": result}

            elif operation == "nearest_neighbors":
                query = kwargs.get("query", "")
                texts = kwargs.get("texts", [])
                k = kwargs.get("k", 5)
                raw = backend.call("nearest_neighbors", query=query, texts=texts, k=k)
                result = raw.get("result", raw) if raw.get("status") == "ok" else raw
                return {
                    "status": "success",
                    "operation": "nearest_neighbors",
                    "result": result,
                }

            elif operation == "constellation_detect":
                coords = kwargs.get("coords", [])
                raw = backend.call("constellation_detect", coords=coords)
                result = raw.get("result", raw) if raw.get("status") == "ok" else raw
                return {
                    "status": "success",
                    "operation": "constellation_detect",
                    "result": result,
                }

            elif operation == "coherence_score":
                coords = kwargs.get("coords", [])
                raw = backend.call("coherence_score", coords=coords)
                result = raw.get("result", raw) if raw.get("status") == "ok" else raw
                return {
                    "status": "success",
                    "operation": "coherence_score",
                    "result": result,
                }

            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}

        except Exception as e:
            logger.exception("Polyglot %s.%s failed", backend_name, operation)
            return {
                "status": "error",
                "error": str(e),
                "error_code": "polyglot_execution_error",
            }


def handle_polyglot_search(**kwargs: Any) -> dict[str, Any]:
    """Convenience: encode query + find nearest neighbors in one call."""
    query = kwargs.get("query", "")
    texts = kwargs.get("texts", [])
    k = kwargs.get("k", 5)
    backend_name = kwargs.get("backend", "auto")

    if not query:
        return {"status": "error", "error": "query is required"}
    if not texts:
        return {"status": "error", "error": "texts is required"}

    try:
        backend_ctx = _resolve_backend(backend_name)
    except RuntimeError as e:
        return {
            "status": "error",
            "error": str(e),
            "error_code": "polyglot_unavailable",
        }
    except ValueError as e:
        return {"status": "error", "error": str(e), "error_code": "invalid_backend"}

    with backend_ctx as backend:
        try:
            # Encode the query
            enc = backend.call("encode", text=query)
            query_coord = enc if enc.get("status") != "ok" else enc.get("result", enc)

            # Find nearest neighbors
            nn = backend.call("nearest_neighbors", query=query, texts=texts, k=k)
            nn_result = nn if nn.get("status") != "ok" else nn.get("result", nn)

            return {
                "status": "success",
                "operation": "search",
                "query_coord": query_coord,
                "nearest_neighbors": nn_result,
            }
        except Exception as e:
            logger.exception("Polyglot %s.search failed", backend_name)
            return {
                "status": "error",
                "error": str(e),
                "error_code": "polyglot_execution_error",
            }


_status_cache: dict[str, Any] = {"result": None, "time": 0.0}


def handle_polyglot_status(**kwargs: Any) -> dict[str, Any]:
    """Check availability of all polyglot backends."""
    # Cache status for 60s to avoid spawning 5 subprocesses on every call
    now = _time.monotonic()
    if _status_cache["result"] is not None and (now - _status_cache["time"]) < 60.0:
        return _status_cache["result"]

    if _wp is None:
        return {
            "status": "error",
            "error": "Polyglot bridge unavailable",
            "backends": {},
        }

    # Skip subprocess pings when polyglot is disabled (test/CI environments)
    if os.environ.get("WM_SKIP_POLYGLOT") == "1":
        result = {
            "status": "success",
            "backends": {},
            "available": 0,
            "total": 0,
            "health_score": 0.0,
            "skipped": True,
            "reason": "WM_SKIP_POLYGLOT=1",
        }
        _status_cache["result"] = result
        _status_cache["time"] = now
        return result

    results: dict[str, Any] = {}
    backends = {
        "julia": _wp.JuliaBackend,
        "elixir": _wp.ElixirBackend,
        "haskell": _wp.HaskellBackend,
        "rust": _wp.RustBackend,
        "koka": _wp.KokaBackend,
        "rust_evolution": _wp.RustEvolutionBackend,
        "julia_yield": _wp.JuliaYieldBackend,
        "elixir_actor": _wp.ElixirActorBackend,
    }

    for name, cls in backends.items():
        try:
            with cls() as backend:
                ping = backend.call("ping", timeout=5.0)
                results[name] = {
                    "available": True,
                    "ping": ping,
                }
        except Exception as e:
            results[name] = {
                "available": False,
                "error": str(e),
            }

    available_count = sum(1 for r in results.values() if r.get("available"))
    total = len(backends)
    health = available_count / total if total > 0 else 0.0

    result = {
        "status": "success",
        "backends": results,
        "health_score": round(health, 2),
        "available": available_count,
        "total": total,
    }
    _status_cache["result"] = result
    _status_cache["time"] = _time.monotonic()
    return result


_evolution_cache: dict[str, Any] = {"backend": None, "time": 0.0}


def _get_evolution_backend() -> Any:
    """Get or reuse a RustEvolutionBackend instance."""
    if _wp is None:
        raise RuntimeError("Polyglot bridge unavailable")
    now = _time.monotonic()
    if (
        _evolution_cache["backend"] is not None
        and (now - _evolution_cache["time"]) < 300.0
    ):
        return _evolution_cache["backend"]
    backend = _wp.RustEvolutionBackend()
    backend.call("ping", timeout=5.0)
    _evolution_cache["backend"] = backend
    _evolution_cache["time"] = now
    return backend


def handle_polyglot_evolution(**kwargs: Any) -> dict[str, Any]:
    """Execute evolution operations through the Rust evolution backend.

    Supported operations: shannon_entropy, kl_divergence, information_gain,
    system_uncertainty, adapt_weights, exploration_score, thermo_cool,
    thermo_reheat, thermo_adapt, boltzmann_probabilities, boltzmann_select,
    hrr_encode, hrr_bind, hrr_unbind, hrr_superposition, hrr_synergy,
    hrr_similarity, mc_run_trials, mc_importance_sampling,
    mc_control_variates, mc_antithetic_variates, cf_project_forward,
    cf_bootstrap_ci, cf_estimate_impact.
    """
    operation = kwargs.get("operation")
    if not operation:
        return {"status": "error", "error": "operation is required"}

    try:
        backend = _get_evolution_backend()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_code": "evolution_unavailable",
        }

    try:
        params = {k: v for k, v in kwargs.items() if k != "operation"}
        raw = backend.call(operation, **params)
        result = raw.get("result", raw) if raw.get("status") == "ok" else raw
        return {"status": "success", "operation": operation, "result": result}
    except Exception as e:
        logger.exception("Evolution backend %s failed", operation)
        return {
            "status": "error",
            "error": str(e),
            "error_code": "evolution_execution_error",
        }


_yield_cache: dict[str, Any] = {"backend": None, "time": 0.0}


def _get_yield_backend() -> Any:
    """Get or reuse a JuliaYieldBackend instance."""
    if _wp is None:
        raise RuntimeError("Polyglot bridge unavailable")
    now = _time.monotonic()
    if _yield_cache["backend"] is not None and (now - _yield_cache["time"]) < 300.0:
        return _yield_cache["backend"]
    backend = _wp.JuliaYieldBackend()
    backend.call("ping", timeout=10.0)
    _yield_cache["backend"] = backend
    _yield_cache["time"] = now
    return backend


def handle_polyglot_yield(**kwargs: Any) -> dict[str, Any]:
    """Execute yield curve operations through the Julia yield backend.

    Supported operations: value_at, duration, fit_parameters,
    portfolio_duration, select_by_horizon, detect_regime_change.
    """
    operation = kwargs.get("operation")
    if not operation:
        return {"status": "error", "error": "operation is required"}

    try:
        backend = _get_yield_backend()
    except Exception as e:
        return {"status": "error", "error": str(e), "error_code": "yield_unavailable"}

    try:
        params = {k: v for k, v in kwargs.items() if k != "operation"}
        raw = backend.call(operation, **params)
        result = raw.get("result", raw) if raw.get("status") == "ok" else raw
        return {"status": "success", "operation": operation, "result": result}
    except Exception as e:
        logger.exception("Yield backend %s failed", operation)
        return {
            "status": "error",
            "error": str(e),
            "error_code": "yield_execution_error",
        }


_actor_cache: dict[str, Any] = {"backend": None, "time": 0.0}


def _get_actor_backend() -> Any:
    """Get or reuse an ElixirActorBackend instance."""
    if _wp is None:
        raise RuntimeError("Polyglot bridge unavailable")
    now = _time.monotonic()
    if _actor_cache["backend"] is not None and (now - _actor_cache["time"]) < 300.0:
        return _actor_cache["backend"]
    backend = _wp.ElixirActorBackend()
    backend.call("ping", timeout=10.0)
    _actor_cache["backend"] = backend
    _actor_cache["time"] = now
    return backend


def handle_polyglot_actor(**kwargs: Any) -> dict[str, Any]:
    """Execute actor operations through the Elixir actor backend.

    Supported operations: start_actor, send_outcome, broadcast_outcome,
    transfer_belief, get_posteriors, get_stats.
    """
    operation = kwargs.get("operation")
    if not operation:
        return {"status": "error", "error": "operation is required"}

    try:
        backend = _get_actor_backend()
    except Exception as e:
        return {"status": "error", "error": str(e), "error_code": "actor_unavailable"}

    try:
        params = {k: v for k, v in kwargs.items() if k != "operation"}
        raw = backend.call(operation, **params)
        result = raw.get("result", raw) if raw.get("status") == "ok" else raw
        return {"status": "success", "operation": operation, "result": result}
    except Exception as e:
        logger.exception("Actor backend %s failed", operation)
        return {
            "status": "error",
            "error": str(e),
            "error_code": "actor_execution_error",
        }
