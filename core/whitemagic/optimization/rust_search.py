"""Rust BM25 Search Bridge.

Extracted from rust_accelerators.py for better separation of concerns.
Provides BM25 full-text search engine with Rust acceleration.
"""
# ruff: noqa: BLE001

import logging
from typing import Any

from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rust availability check
# ---------------------------------------------------------------------------

_RUST_SEARCH = False
_rs: Any = None

try:
    import whitemagic_rust as _rs_mod
    _rs = _rs_mod
except ImportError:
    try:
        import whitemagic_rs as _rs_mod
        _rs = _rs_mod
    except ImportError:
        pass

if _rs is not None and hasattr(_rs, "search_build_index"):
    _RUST_SEARCH = True
    logger.debug("Rust BM25 search engine available")


def rust_search_available() -> bool:
    """Check if Rust BM25 search engine is available."""
    return _RUST_SEARCH


def search_build_index(
    documents: list[dict[str, str]],
) -> str | None:
    """Build a BM25 inverted index from documents.

    Args:
        documents: List of dicts with keys: id, title, content.

    Returns:
        JSON string of index handle/stats, or None if Rust unavailable.

    """
    if not _RUST_SEARCH:
        return None
    try:
        docs_json = _json_dumps(documents)
        result: str = _rs.search_build_index(docs_json)
        return result
    except Exception as e:
        logger.debug(f"Rust search_build_index failed: {e}")
        return None


def search_query(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]] | None:
    """Query the BM25 global index with a text query.
    Call search_build_index() first to populate the index.

    Returns:
        List of {id, score} dicts sorted by relevance, or None.

    """
    if not _RUST_SEARCH:
        return None
    try:
        results_json: str = _rs.search_query(query, limit)
        parsed = _json_loads(results_json)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        return None
    except Exception as e:
        logger.debug(f"Rust search_query failed: {e}")
        return None


def search_fuzzy(
    query: str,
    limit: int = 10,
    max_distance: int = 2,
) -> list[dict[str, Any]] | None:
    """Fuzzy search the global BM25 index with Levenshtein edit distance tolerance.
    Call search_build_index() first to populate the index.

    Returns:
        List of {id, score} dicts, or None.

    """
    if not _RUST_SEARCH:
        return None
    try:
        results_json: str = _rs.search_fuzzy(query, limit, max_distance)
        parsed = _json_loads(results_json)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        return None
    except Exception as e:
        logger.debug(f"Rust search_fuzzy failed: {e}")
        return None


def search_and_query(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]] | None:
    """Boolean AND query the global BM25 index — all terms must appear.
    Call search_build_index() first to populate the index.

    Returns:
        List of {id, score} dicts, or None.

    """
    if not _RUST_SEARCH:
        return None
    try:
        results_json: str = _rs.search_boolean_and(query, limit)
        parsed = _json_loads(results_json)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        return None
    except Exception as e:
        logger.debug(f"Rust search_and_query failed: {e}")
        return None


def search_stats() -> dict[str, Any] | None:
    """Get global index statistics (doc count, vocab size, avg doc length).
    Call search_build_index() first to populate the index.

    Returns:
        Dict with index stats, or None.

    """
    if not _RUST_SEARCH:
        return None
    try:
        stats_json: str = _rs.search_stats()
        parsed = _json_loads(stats_json)
        if isinstance(parsed, dict):
            return parsed
        return None
    except Exception as e:
        logger.debug(f"Rust search_stats failed: {e}")
        return None
