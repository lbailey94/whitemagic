"""Polyglot Memory Handlers — Bridge holographic memory queries to Julia/Elixir/Haskell/Rust.

Dynamically adds the polyglot bridge path to sys.path and monkey-patches
POLYGLOT_ROOT so the bridge resolves files correctly regardless of import context.
"""
# ruff: noqa: BLE001

import logging
import sys
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

# Import and patch root path
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
        return {"status": "error", "error": str(e), "error_code": "polyglot_unavailable"}
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
                return {"status": "success", "operation": "nearest_neighbors", "result": result}

            elif operation == "constellation_detect":
                coords = kwargs.get("coords", [])
                raw = backend.call("constellation_detect", coords=coords)
                result = raw.get("result", raw) if raw.get("status") == "ok" else raw
                return {"status": "success", "operation": "constellation_detect", "result": result}

            elif operation == "coherence_score":
                coords = kwargs.get("coords", [])
                raw = backend.call("coherence_score", coords=coords)
                result = raw.get("result", raw) if raw.get("status") == "ok" else raw
                return {"status": "success", "operation": "coherence_score", "result": result}

            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}

        except Exception as e:
            logger.exception("Polyglot %s.%s failed", backend_name, operation)
            return {"status": "error", "error": str(e), "error_code": "polyglot_execution_error"}


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
        return {"status": "error", "error": str(e), "error_code": "polyglot_unavailable"}
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
            return {"status": "error", "error": str(e), "error_code": "polyglot_execution_error"}


def handle_polyglot_status(**kwargs: Any) -> dict[str, Any]:
    """Check availability of all polyglot backends."""
    if _wp is None:
        return {
            "status": "error",
            "error": "Polyglot bridge unavailable",
            "backends": {},
        }

    results: dict[str, Any] = {}
    backends = {
        "julia": _wp.JuliaBackend,
        "elixir": _wp.ElixirBackend,
        "haskell": _wp.HaskellBackend,
        "rust": _wp.RustBackend,
        "koka": _wp.KokaBackend,
    }

    for name, cls in backends.items():
        try:
            with cls() as backend:
                ping = backend.call("ping")
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

    return {
        "status": "success",
        "backends": results,
        "health_score": round(health, 2),
        "available": available_count,
        "total": total,
    }
