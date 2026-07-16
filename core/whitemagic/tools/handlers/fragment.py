"""Fragment — Rust-powered codebase search handler.

Provides a 3-layer integration with Fragment's Rust core:
  1. PyO3 (import fragment) — tightest, fastest
  2. HTTP (localhost:7727) — persistent server
  3. Subprocess (fragment CLI) — fallback

Each layer returns the same dict structure. Graceful degradation
means the handler always works — just slower if Rust isn't available.

Tools exposed:
  fragment.search — search a codebase index for relevant chunks
  fragment.index  — build or update a codebase index
  fragment.status — show index statistics
  fragment.query  — alias for fragment.search

Also augments existing Winnowing Basket tools (vector.search,
hybrid_recall, search_query) with Fragment acceleration when available.
"""
# ruff: noqa: BLE001

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_FRAGMENT_BIN = Path(
    os.environ.get(
        "FRAGMENT_BIN",
        str(
            Path(__file__).resolve().parent.parent.parent.parent.parent
            / "aux"
            / "fragment"
            / "target"
            / "release"
            / "fragment"
        ),
    )
)

_FRAGMENT_HTTP_URL = os.environ.get("FRAGMENT_HTTP_URL", "http://127.0.0.1:7727")
_FRAGMENT_TIMEOUT = int(os.environ.get("FRAGMENT_TIMEOUT", "30"))
_FRAGMENT_INDEX_TIMEOUT = int(os.environ.get("FRAGMENT_INDEX_TIMEOUT", "300"))

_pyo3_module: Any = None
_pyo3_checked: bool = False


def _get_pyo3() -> Any:
    """Try to import the Fragment PyO3 module. Returns None if unavailable."""
    global _pyo3_module, _pyo3_checked
    if _pyo3_checked:
        return _pyo3_module
    _pyo3_checked = True
    try:
        import fragment as _frag  # type: ignore[import-not-found]

        if hasattr(_frag, "is_available") and _frag.is_available():
            _pyo3_module = _frag
            logger.info("Fragment PyO3 module loaded — using native Rust core")
        else:
            _pyo3_module = None
    except ImportError:
        _pyo3_module = None
    except Exception as e:
        logger.debug("Fragment PyO3 import failed: %s", e)
        _pyo3_module = None
    return _pyo3_module


def _http_available() -> bool:
    """Check if Fragment HTTP server is running."""
    try:
        import urllib.request

        req = urllib.request.Request(
            f"{_FRAGMENT_HTTP_URL}/api/health",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _binary_available() -> bool:
    """Check if Fragment CLI binary exists."""
    return _FRAGMENT_BIN.exists() and os.access(_FRAGMENT_BIN, os.X_OK)


def get_fragment_layer() -> str:
    """Return the best available Fragment layer: 'pyo3', 'http', 'subprocess', or 'none'."""
    if _get_pyo3() is not None:
        return "pyo3"
    if _http_available():
        return "http"
    if _binary_available():
        return "subprocess"
    return "none"


def _pyo3_index(
    path: str, mode: str, force: bool, output: str | None
) -> dict[str, Any]:
    frag = _get_pyo3()
    if frag is None:
        raise RuntimeError("PyO3 not available")
    return frag.index(path, mode=mode, force=force, output=output)


def _pyo3_query(
    path: str, query: str, top: int, index_dir: str | None
) -> dict[str, Any]:
    frag = _get_pyo3()
    if frag is None:
        raise RuntimeError("PyO3 not available")
    return frag.query(path, query, top=top, index_dir=index_dir)


def _pyo3_status(path: str, index_dir: str | None) -> dict[str, Any]:
    frag = _get_pyo3()
    if frag is None:
        raise RuntimeError("PyO3 not available")
    return frag.status(path, index_dir=index_dir)


def _http_index(
    path: str, mode: str, force: bool, output: str | None
) -> dict[str, Any]:
    import urllib.request

    payload = json.dumps({"path": path, "mode": mode, "force": force}).encode()
    req = urllib.request.Request(
        f"{_FRAGMENT_HTTP_URL}/api/index",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_FRAGMENT_INDEX_TIMEOUT) as resp:
        return json.loads(resp.read())


def _http_query(
    path: str, query: str, top: int, index_dir: str | None
) -> dict[str, Any]:
    import urllib.request

    payload = json.dumps({"q": query, "top": top, "path": path}).encode()
    req = urllib.request.Request(
        f"{_FRAGMENT_HTTP_URL}/api/query",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_FRAGMENT_TIMEOUT) as resp:
        data = json.loads(resp.read())
        # Normalize HTTP response to match PyO3 format
        if "results" in data and isinstance(data["results"], list):
            return data
        return {
            "query": query,
            "top": top,
            "results": data.get("results", []),
            "count": len(data.get("results", [])),
        }


def _http_status(path: str, index_dir: str | None) -> dict[str, Any]:
    import urllib.request

    req = urllib.request.Request(
        f"{_FRAGMENT_HTTP_URL}/api/status?path={path}",
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def _subprocess_index(
    path: str, mode: str, force: bool, output: str | None
) -> dict[str, Any]:
    cmd = [str(_FRAGMENT_BIN), "index", path, "--mode", mode]
    if force:
        cmd.append("--force")
    if output:
        cmd.extend(["--output", output])
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=_FRAGMENT_INDEX_TIMEOUT
    )
    if result.returncode != 0:
        raise RuntimeError(f"Fragment index failed: {result.stderr}")
    return {
        "file_count": 0,
        "chunk_count": 0,
        "source_bytes": 0,
        "index_bytes": 0,
        "duration_secs": 0.0,
        "mode": mode,
        "index_dir": output or str(Path(path) / ".fragment"),
        "stdout": result.stdout,
    }


def _subprocess_query(
    path: str, query: str, top: int, index_dir: str | None
) -> dict[str, Any]:
    cmd = [
        str(_FRAGMENT_BIN),
        "query",
        path,
        query,
        "--top",
        str(top),
        "--format",
        "json",
    ]
    if index_dir:
        cmd.extend(["--index", index_dir])
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=_FRAGMENT_TIMEOUT
    )
    if result.returncode != 0:
        raise RuntimeError(f"Fragment query failed: {result.stderr}")
    if "No index found" in result.stdout:
        raise RuntimeError(f"No Fragment index found at {path}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "query": query,
            "top": top,
            "results": [],
            "count": 0,
            "raw": result.stdout,
        }
    return data


def _subprocess_status(path: str, index_dir: str | None) -> dict[str, Any]:
    if not _binary_available():
        return {"exists": False, "path": path}
    cmd = [str(_FRAGMENT_BIN), "status", path]
    if index_dir:
        cmd.extend(["--index", index_dir])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        return {"exists": False, "path": path}
    meta: dict[str, Any] = {"exists": True}
    for line in result.stdout.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            try:
                meta[key] = int(val)
            except ValueError:
                try:
                    meta[key] = float(val)
                except ValueError:
                    meta[key] = val
    return meta


def _dispatch_index(
    path: str, mode: str = "quick", force: bool = False, output: str | None = None
) -> dict[str, Any]:
    """Index a codebase using the best available Fragment layer."""
    # Layer 1: PyO3
    try:
        return _pyo3_index(path, mode, force, output)
    except Exception as e:
        logger.debug("Fragment PyO3 index failed: %s", e)

    # Layer 2: HTTP
    try:
        return _http_index(path, mode, force, output)
    except Exception as e:
        logger.debug("Fragment HTTP index failed: %s", e)

    # Layer 3: Subprocess
    return _subprocess_index(path, mode, force, output)


def _dispatch_query(
    path: str, query: str, top: int = 10, index_dir: str | None = None
) -> dict[str, Any]:
    """Query a Fragment index using the best available layer."""
    # Layer 1: PyO3
    try:
        return _pyo3_query(path, query, top, index_dir)
    except Exception as e:
        logger.debug("Fragment PyO3 query failed: %s", e)

    # Layer 2: HTTP
    try:
        return _http_query(path, query, top, index_dir)
    except Exception as e:
        logger.debug("Fragment HTTP query failed: %s", e)

    # Layer 3: Subprocess
    return _subprocess_query(path, query, top, index_dir)


def _dispatch_status(path: str, index_dir: str | None = None) -> dict[str, Any]:
    """Get Fragment index status using the best available layer."""
    try:
        return _pyo3_status(path, index_dir)
    except Exception as e:
        logger.debug("Fragment PyO3 status failed: %s", e)

    try:
        return _http_status(path, index_dir)
    except Exception as e:
        logger.debug("Fragment HTTP status failed: %s", e)

    return _subprocess_status(path, index_dir)


def handle_fragment_search(**kwargs: Any) -> dict[str, Any]:
    """Search a codebase index for relevant code chunks using Fragment (Rust)."""
    path = kwargs.get("path", "")
    query = kwargs.get("query", kwargs.get("q", ""))
    top = int(kwargs.get("top", kwargs.get("limit", 10)))
    index_dir = kwargs.get("index_dir")

    if not path:
        return {"status": "error", "error": "path is required"}
    if not query:
        return {"status": "error", "error": "query is required"}

    try:
        result = _dispatch_query(path, query, top, index_dir)
        return {
            "status": "success",
            "query": query,
            "results": result.get("results", []),
            "count": result.get("count", len(result.get("results", []))),
            "layer": get_fragment_layer(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "layer": get_fragment_layer()}


def handle_fragment_index(**kwargs: Any) -> dict[str, Any]:
    """Build or update a Fragment index for a codebase."""
    path = kwargs.get("path", "")
    mode = kwargs.get("mode", "quick")
    force = bool(kwargs.get("force", False))
    output = kwargs.get("output")

    if not path:
        return {"status": "error", "error": "path is required"}

    try:
        result = _dispatch_index(path, mode, force, output)
        return {
            "status": "success",
            "index_dir": result.get("index_dir", str(Path(path) / ".fragment")),
            "file_count": result.get("file_count", 0),
            "chunk_count": result.get("chunk_count", 0),
            "duration_secs": result.get("duration_secs", 0.0),
            "mode": result.get("mode", mode),
            "layer": get_fragment_layer(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "layer": get_fragment_layer()}


def handle_fragment_status(**kwargs: Any) -> dict[str, Any]:
    """Show Fragment index statistics for a project."""
    path = kwargs.get("path", "")
    index_dir = kwargs.get("index_dir")

    if not path:
        return {"status": "error", "error": "path is required"}

    try:
        result = _dispatch_status(path, index_dir)
        return {
            "status": "success",
            "layer": get_fragment_layer(),
            **result,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "layer": get_fragment_layer()}


def handle_fragment_query(**kwargs: Any) -> dict[str, Any]:
    """Alias for fragment.search — query a Fragment index."""
    return handle_fragment_search(**kwargs)


def fragment_accelerated_search(
    query: str, path: str | None = None, top: int = 10
) -> dict[str, Any] | None:
    """Try Fragment-accelerated search. Returns None if Fragment is unavailable
    or no index exists, so callers can fall back to the Python implementation.

    This is called by handle_vector_search and handle_hybrid_recall when
    a codebase path is provided.
    """
    if not path:
        return None

    layer = get_fragment_layer()
    if layer == "none":
        return None

    try:
        status = _dispatch_status(path)
        if not status.get("exists", False):
            return None
    except Exception:
        return None

    # Use Fragment for the search
    try:
        result = _dispatch_query(path, query, top)
        return {
            "accelerated": True,
            "layer": layer,
            "results": result.get("results", []),
            "count": result.get("count", 0),
        }
    except Exception as e:
        logger.debug("Fragment accelerated search failed, falling back: %s", e)
        return None
