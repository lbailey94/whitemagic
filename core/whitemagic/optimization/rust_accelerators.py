"""Rust Accelerator Bridge — Try Rust, Fall Back to Python
========================================================
Provides unified access to the Rust accelerators with
automatic fallback to pure-Python implementations when the
Rust extension (whitemagic_rs) is not available.

Accelerators (v12.3):
  - Galactic batch scoring (7-signal retention + distance)
  - Association mining (keyword extraction + N² Jaccard overlap)
  - 5D Spatial Index (KD-tree with V dimension)

Accelerators (v13.1):
  - 5D Holographic encoding (batch Rayon, garden/element blending)
  - MinHash LSH (128-hash near-duplicate detection)
  - SQLite batch operations (galactic updates, FTS5, zone stats)

Usage:
    from whitemagic.optimization.rust_accelerators import (
        galactic_batch_score,
        association_mine,
        get_spatial_index_5d,
    )
"""
# ruff: noqa: BLE001

import logging
import sqlite3
from typing import Any, cast

from whitemagic.optimization._rust_fallbacks import (
    PythonSpatialIndex5D,
    _association_mine_python,
    _galactic_batch_score_python,
)

# Import extracted mining/arrow operations
from whitemagic.optimization.rust_mining import (  # noqa: F401
    arrow_available,
    arrow_decode_memories,
    arrow_encode_memories,
    arrow_roundtrip_bench,
    arrow_schema_info,
    get_galaxy_stats,
    get_geneseed_stats,
    mine_access_patterns,
    mine_cache_candidates,
    mine_geneseed_patterns,
    mine_semantic_clusters,
)

# Import extracted rate limiter operations
from whitemagic.optimization.rust_rate_limit import (  # noqa: F401
    rate_check,
    rate_check_batch,
    rate_set_override,
    rate_stats,
    rust_rate_limiter_available,
)

# Import extracted search operations
from whitemagic.optimization.rust_search import (  # noqa: F401
    rust_search_available,
    search_and_query,
    search_build_index,
    search_fuzzy,
    search_query,
    search_stats,
)

# Import extracted tokio/ipc operations
from whitemagic.optimization.rust_tokio import (  # noqa: F401
    ipc_available,
    ipc_status,
    tokio_clone_bench,
    tokio_clone_stats,
    tokio_clones_available,
    tokio_deploy_clones,
)
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rust availability check
# ---------------------------------------------------------------------------

_RUST_AVAILABLE = False
_RUST_V131 = False
_rs: Any = None

try:
    import whitemagic_rust as _rs_mod
    _rs = _rs_mod
    _HAS_RUST = True
except ImportError:
    try:
        import whitemagic_rs as _rs_mod
        _rs = _rs_mod
        _HAS_RUST = True
    except ImportError:
        _rs = None
        _HAS_RUST = False

if _rs is not None:
    # Check for v12.3 accelerator functions
    if hasattr(_rs, "galactic_batch_score"):
        _RUST_AVAILABLE = True
        logger.debug("Rust v12.3 accelerators loaded")
    else:
        logger.debug("Rust extension found but missing v12.3 accelerators")

    # Check for v15.10 galaxy miner functions
    if hasattr(_rs, "mine_access_patterns"):
        logger.debug("Rust v15.10 galaxy miner loaded")

    # Check for v13.1 features (holographic/minhash)
    if hasattr(_rs, "holographic_encode_batch"):
        _RUST_V131 = True
        logger.debug("Rust v13.1 accelerators loaded")


def rust_available() -> bool:
    """Check if Rust accelerators are available."""
    return _RUST_AVAILABLE


def rust_v131_available() -> bool:
    """Check if v13.1 Rust accelerators (holographic, minhash, sqlite) are available."""
    return _RUST_V131


# ---------------------------------------------------------------------------
# Galactic Batch Scoring
# ---------------------------------------------------------------------------

def galactic_batch_score(
    memories: list[dict[str, Any]],
    quick: bool = False,
) -> list[dict[str, Any]]:
    """Score a batch of memories for galactic distance.

    PSR-015: Uses native FFI (zero JSON overhead) when available for 50× speedup.

    Args:
        memories: List of dicts with keys: id, importance, neuro_score,
                  emotional_valence, recall_count, is_protected, etc.
        quick: If True, use 4-signal heuristic (faster, less precise).

    Returns:
        List of dicts with: id, retention_score, galactic_distance, zone.

    """
    # PSR-015: Try native FFI first (zero JSON overhead)
    if _RUST_AVAILABLE:
        try:
            import whitemagic_rs
            if hasattr(whitemagic_rs, "galactic_batch_score_native"):
                # Convert list of dicts to PyList of PyDicts for native FFI
                results = whitemagic_rs.galactic_batch_score_native(memories, quick)
                if results:
                    # Convert PyList of PyDicts back to Python list
                    return [dict(item) for item in results]  # type: ignore
        except BaseException as e:  # catches Rust PanicException (not a subclass of Exception)
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            logger.debug(f"Native galactic scoring failed, trying JSON path: {e}")

    # JSON path (with serialization overhead)
    if _RUST_AVAILABLE:
        try:
            memories_json = _json_dumps(memories)
            if quick:
                result_json = _rs.galactic_batch_score_quick(memories_json)
            else:
                result_json = _rs.galactic_batch_score(memories_json)
            parsed: list[dict[str, Any]] = _json_loads(result_json)
            return parsed
        except Exception as e:
            logger.debug(f"Rust galactic scoring failed, using Python: {e}")

    # Python fallback
    return cast(list[dict[str, Any]], _galactic_batch_score_python(memories, quick))


# ---------------------------------------------------------------------------
# Association Mining
# ---------------------------------------------------------------------------

def association_mine(
    texts: list[tuple[str, str]],
    max_keywords: int = 50,
    min_score: float = 0.3,
    max_results: int = 500,
) -> dict[str, Any]:
    """Extract keywords from texts and compute pairwise overlaps.

    PSR-015: Uses native FFI (zero JSON overhead) when available for 25× speedup.

    Args:
        texts: List of (memory_id, text_content) tuples.
        max_keywords: Max keywords to extract per text.
        min_score: Minimum overlap score to include.
        max_results: Maximum overlap results to return.

    Returns:
        Dict with memory_count, pair_count, overlaps.

    """
    # PSR-015: Try native FFI first (zero JSON overhead)
    if _RUST_AVAILABLE:
        try:
            import whitemagic_rs
            if hasattr(whitemagic_rs, "association_mine_native"):
                results = whitemagic_rs.association_mine_native(
                    texts, max_keywords, min_score, max_results
                )
                if results:
                    d = dict(results)  # type: ignore
                    # Normalize: native path omits pair_count — add it for API consistency
                    if "pair_count" not in d:
                        d["pair_count"] = len(d.get("overlaps", []))
                    return d
        except Exception as e:
            logger.debug(f"Native association mining failed, trying JSON path: {e}")

    # JSON path (with serialization overhead)
    if _RUST_AVAILABLE:
        try:
            texts_json = _json_dumps(texts)
            result_json = _rs.association_mine_fast(
                texts_json, max_keywords, min_score, max_results,
            )
            parsed: dict[str, Any] = _json_loads(result_json)
            return parsed
        except Exception as e:
            logger.debug(f"Rust association mining failed, using Python: {e}")

    # Python fallback
    return cast(dict[str, Any], _association_mine_python(texts, max_keywords, min_score, max_results))


# ---------------------------------------------------------------------------
# 5D Spatial Index
# ---------------------------------------------------------------------------

_index_5d: Any = None


def get_spatial_index_5d() -> Any:
    """Get or create the global 5D spatial index (Rust or Python fallback)."""
    global _index_5d
    if _index_5d is None:
        if _RUST_AVAILABLE:
            try:
                _index_5d = _rs.SpatialIndex5D()
                logger.debug("Using Rust 5D spatial index")
                return _index_5d
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug("Exception silenced: %s", e)
        # Python fallback — thin wrapper over the 4D index
        _index_5d = PythonSpatialIndex5D()
        logger.debug("Using Python 5D spatial index fallback")
    return _index_5d


# ---------------------------------------------------------------------------
# v13.1 — 5D Holographic Encoder (Rust Rayon batch)
# ---------------------------------------------------------------------------

def _prepare_memory_for_rust(memory: dict[str, Any]) -> dict[str, Any]:
    """Normalize a memory dict to the shape expected by Rust MemoryInput."""
    from datetime import datetime
    content = str(memory.get("content", ""))
    title = str(memory.get("title", ""))
    combined = f"{title} {content}" if title else content

    # Calculate age_days from created_at
    age_days = 0.0
    ts = memory.get("created_at") or memory.get("timestamp")
    if ts and isinstance(ts, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(ts[:26], fmt)
                age_days = max(0.0, (datetime.now() - dt).total_seconds() / 86400.0)
                break
            except ValueError:
                continue

    # Extract garden from metadata or tags
    metadata = memory.get("metadata") or {}
    garden = metadata.get("garden", "")
    if not garden:
        tags = memory.get("tags") or []
        for t in tags:
            if t in ("wood", "fire", "earth", "metal", "water"):
                garden = t
                break

    return {
        "id": memory.get("id", "unknown"),
        "content": combined,
        "importance": memory.get("importance") or 0.5,
        "access_count": memory.get("access_count") or memory.get("recall_count") or 0,
        "age_days": age_days,
        "galactic_distance": memory.get("galactic_distance") or 0.0,
        "garden": garden,
        "tags": list(memory.get("tags") or []),
    }


def holographic_encode_batch(
    memories: list[dict[str, Any]],
) -> list[dict[str, float]] | None:
    """Batch-encode memories into 5D holographic coordinates using Rust.

    Args:
        memories: List of memory dicts with keys: content, title, tags,
                  emotional_valence, importance, neuro_score, memory_type,
                  created_at, galactic_distance, retention_score, etc.

    Returns:
        List of {"x", "y", "z", "w", "v"} coordinate dicts, or None if
        Rust is not available.

    """
    if not _RUST_V131:
        return None
    try:
        prepared = [_prepare_memory_for_rust(m) for m in memories]
        memories_json = _json_dumps(prepared)
        result_json = _rs.holographic_encode_batch(memories_json)
        parsed: list[dict[str, float]] = _json_loads(result_json)
        return parsed
    except Exception as e:
        logger.debug(f"Rust holographic batch encoding failed: {e}")
        return None


def holographic_encode_single(
    memory: dict[str, Any],
) -> dict[str, float] | None:
    """Encode a single memory into 5D holographic coordinates using Rust.

    Returns:
        {"x", "y", "z", "w", "v"} coordinate dict, or None if Rust
        is not available.

    """
    if not _RUST_V131:
        return None
    try:
        prepared = _prepare_memory_for_rust(memory)
        memory_json = _json_dumps(prepared)
        result_json = _rs.holographic_encode_single(memory_json)
        parsed: dict[str, float] = _json_loads(result_json)
        return parsed
    except Exception as e:
        logger.debug(f"Rust holographic single encoding failed: {e}")
        return None


def holographic_nearest_5d(
    query: list[float],
    coords: list[dict[str, Any]],
    k: int = 10,
    weights: list[float] | None = None,
) -> list[dict[str, Any]] | None:
    """Find k-nearest neighbors in 5D holographic space using Rust.

    Args:
        query: [x, y, z, w, v] query vector.
        coords: List of {"id", "x", "y", "z", "w", "v"} dicts.
        k: Number of nearest neighbors.
        weights: Optional [wx, wy, wz, ww, wv] axis weights.

    Returns:
        List of {"id", "distance"} dicts, or None if Rust not available.

    """
    if not _RUST_V131:
        return None
    try:
        query_json = _json_dumps(query)
        coords_json = _json_dumps(coords)
        weights_json = _json_dumps(weights) if weights else ""
        result_json = _rs.holographic_nearest_5d(query_json, coords_json, k, weights_json)
        parsed: list[dict[str, Any]] = _json_loads(result_json)
        return parsed
    except Exception as e:
        logger.debug(f"Rust holographic nearest 5D failed: {e}")
        return None


# ---------------------------------------------------------------------------
# v13.1 — MinHash LSH (near-duplicate detection)
# ---------------------------------------------------------------------------

def minhash_find_duplicates(
    keyword_sets: list[list[str]],
    threshold: float = 0.5,
    max_results: int = 500,
) -> list[dict[str, Any]] | None:
    """Find near-duplicate memory pairs using MinHash LSH.

    Args:
        keyword_sets: List of keyword lists (one per memory).
        threshold: Minimum estimated Jaccard similarity.
        max_results: Maximum candidate pairs to return.

    Returns:
        List of {"i", "j", "estimated_jaccard"} dicts, or None.

    """
    if not _RUST_V131:
        return None
    try:
        keywords_json = _json_dumps(keyword_sets)
        result_json = _rs.minhash_find_duplicates(keywords_json, threshold, max_results)
        parsed: list[dict[str, Any]] = _json_loads(result_json)
        return parsed
    except Exception as e:
        logger.debug(f"Rust MinHash find_duplicates failed: {e}")
        return None


def minhash_signatures(
    keyword_sets: list[list[str]],
) -> list[list[int]] | None:
    """Compute MinHash signatures for keyword sets.

    Args:
        keyword_sets: List of keyword lists (one per memory).

    Returns:
        List of 128-element signature vectors, or None.

    """
    if not _RUST_V131:
        return None
    try:
        keywords_json = _json_dumps(keyword_sets)
        result_json = _rs.minhash_signatures(keywords_json)
        parsed: list[list[int]] = _json_loads(result_json)
        return parsed
    except Exception as e:
        logger.debug(f"Rust MinHash signatures failed: {e}")
        return None


# ---------------------------------------------------------------------------
# v13.1 — SQLite Accelerator (batch operations)
# ---------------------------------------------------------------------------

def sqlite_batch_update_galactic(
    db_path: str,
    updates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Batch-update galactic distances in SQLite using Rust.

    Args:
        db_path: Path to the SQLite database.
        updates: List of {"id", "galactic_distance", "retention_score"} dicts.

    Returns:
        Result dict with "updated" count, or None if Rust not available.

    """
    if not _RUST_V131:
        return None
    try:
        updates_json = _json_dumps(updates)
        result_json = _rs.sqlite_batch_update_galactic(db_path, updates_json)
        parsed: dict[str, Any] = _json_loads(result_json)
        return parsed
    except (sqlite3.Error, sqlite3.OperationalError) as e:
        logger.debug(f"Rust SQLite batch update failed: {e}")
        return None


def sqlite_decay_drift(
    db_path: str,
    drift_amount: float = 0.005,
    max_distance: float = 0.95,
) -> dict[str, Any] | None:
    """Apply decay drift to inactive memories using Rust SQLite accelerator.

    Returns:
        Result dict with "drifted" count, or None.

    """
    if not _RUST_V131:
        return None
    try:
        result_json = _rs.sqlite_decay_drift(db_path, drift_amount, max_distance)
        parsed: dict[str, Any] = _json_loads(result_json)
        return parsed
    except (sqlite3.Error, sqlite3.OperationalError) as e:
        logger.debug(f"Rust SQLite decay drift failed: {e}")
        return None


def sqlite_fts_search(
    db_path: str,
    query: str,
    limit: int = 50,
    min_importance: float = 0.0,
) -> list[dict[str, Any]] | None:
    """FTS5 search with galactic weighting using Rust SQLite accelerator.

    Returns:
        List of matching memory dicts, or None.

    """
    if not _RUST_V131:
        return None
    try:
        result_json = _rs.sqlite_fts_search(db_path, query, limit, min_importance)
        parsed: list[dict[str, Any]] = _json_loads(result_json)
        return parsed
    except (ImportError, ModuleNotFoundError) as e:
        logger.debug(f"Rust SQLite FTS search failed: {e}")
        return None


def sqlite_zone_stats(
    db_path: str,
) -> dict[str, Any] | None:
    """Get galactic zone statistics using Rust SQLite accelerator.

    Returns:
        Dict with zone counts and stats, or None.

    """
    if not _RUST_V131:
        return None
    try:
        result_json = _rs.sqlite_zone_stats(db_path)
        parsed: dict[str, Any] = _json_loads(result_json)
        return parsed
    except (sqlite3.Error, sqlite3.OperationalError) as e:
        logger.debug(f"Rust SQLite zone stats failed: {e}")
        return None


def sqlite_export_for_mining(
    db_path: str,
    max_distance: float = 0.85,
    min_importance: float = 0.3,
    limit: int = 2000,
) -> list[dict[str, Any]] | None:
    """Export memories for association mining using Rust SQLite accelerator.

    Returns:
        List of memory dicts suitable for mining, or None.

    """
    if not _RUST_V131:
        return None
    try:
        result_json = _rs.sqlite_export_for_mining(db_path, max_distance, min_importance, limit)
        parsed: list[dict[str, Any]] = _json_loads(result_json)
        return parsed
    except (ImportError, ModuleNotFoundError) as e:
        logger.debug(f"Rust SQLite export for mining failed: {e}")
        return None


# ---------------------------------------------------------------------------
# v13.3.2 — Multi-pass Retrieval Pipeline
# ---------------------------------------------------------------------------

_RUST_PIPELINE = False
try:
    if _rs and hasattr(_rs, "retrieval_pipeline"):
        _RUST_PIPELINE = True
        logger.debug("Rust retrieval pipeline available")
except Exception as e:
    import logging
    logging.getLogger(__name__).debug("Exception silenced: %s", e)


def retrieval_pipeline(
    candidates: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]] | None:
    """Execute a multi-pass retrieval pipeline in a single FFI call."""
    if not _RUST_PIPELINE:
        return None
    try:
        # v14: Native PyList/PyDict — no JSON serialization on either side
        if hasattr(_rs, "retrieval_pipeline_native"):
            native_results = _rs.retrieval_pipeline_native(candidates, config or {})
            if isinstance(native_results, list):
                return [dict(item) for item in native_results if isinstance(item, dict)]
        # Fallback to JSON path
        input_data = _json_dumps({
            "candidates": candidates,
            "config": config or {},
        })
        result_json = _rs.retrieval_pipeline(input_data)
        parsed = _json_loads(result_json)
        if isinstance(parsed, list):
            return [dict(item) for item in parsed if isinstance(item, dict)]
        return None
    except Exception as e:
        logger.debug(f"Rust retrieval_pipeline failed: {e}")
        return None


# ---------------------------------------------------------------------------
# v13.3.2 — Keyword Extraction (replaces Zig ctypes path)
# ---------------------------------------------------------------------------

_RUST_KEYWORDS = False
try:
    if _rs and hasattr(_rs, "keyword_extract"):
        _RUST_KEYWORDS = True
        logger.debug("Rust keyword extraction available")
except Exception as e:
    import logging
    logging.getLogger(__name__).debug("Exception silenced: %s", e)


def rust_keywords_available() -> bool:
    """Check if Rust keyword extraction is available."""
    return _RUST_KEYWORDS


def keyword_extract(text: str, max_keywords: int = 50) -> set[str] | None:
    """Extract keywords from text using Rust.

    Returns a set of keywords, or None if Rust is unavailable.
    PyO3 zero-copy string borrowing makes this 5-20× faster than
    the Zig ctypes path and competitive with Python for small texts.
    """
    if not _RUST_KEYWORDS:
        return None
    try:
        result = _rs.keyword_extract(text, max_keywords)
        return cast(set[str], result)
    except Exception as e:
        logger.debug(f"Rust keyword_extract failed: {e}")
        return None


def keyword_extract_batch(texts: list[str], max_keywords: int = 50) -> list[set[str]] | None:
    """Batch extract keywords from multiple texts using Rust.

    Returns a list of keyword sets, or None if Rust is unavailable.
    """
    if not _RUST_KEYWORDS:
        return None
    try:
        result = _rs.keyword_extract_batch(texts, max_keywords)
        return cast(list[set[str]], result)
    except Exception as e:
        logger.debug(f"Rust keyword_extract_batch failed: {e}")
        return None
