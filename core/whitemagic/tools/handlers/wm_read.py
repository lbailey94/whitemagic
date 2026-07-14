# ruff: noqa: BLE001
"""wm_read — Unified Read Interface to the WhiteMagic Cognitive Stack.

Single entry point for all read operations. Auto-selects the best strategy
based on query characteristics, or delegates to an explicit mode.

Modes:
  auto          — Auto-detect best strategy (default)
  hybrid        — Vector + graph RRF fusion (CoreAccessLayer)
  graph_walk    — Anchor search + multi-hop graph walk (GraphWalker)
  semantic      — Embedding similarity search (EmbeddingEngine)
  lexical       — FTS5 BM25 full-text search (UnifiedMemory)
  spatial       — 5D holographic KNN (CoreAccessLayer)
  constellation — Constellation context query (CoreAccessLayer)
  temporal      — Time-bucketed activity metrics (CoreAccessLayer)
  codebase      — Fragment (Rust) accelerated codebase search
  strata        — STRATA static analysis (80+ checkers across 15 languages)
  id            — Direct memory recall by ID (UnifiedMemory)

Usage via dispatch:
    dispatch("wm_read", query="memory consolidation", mode="auto", limit=10)
    dispatch("wm_read", query="mem_abc123", mode="id")
    dispatch("wm_read", query="rust acceleration", mode="codebase", path="/repo")
    dispatch("wm_read", mode="constellation", tags=["rust", "memory"])
    dispatch("wm_read", mode="temporal", time_window="30d")
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _flag_enabled(value: Any) -> bool:
    """Treat only explicit bool/int values as privacy flags."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return False


def _filter_private(memories: list[Any], include_private: bool) -> list[Any]:
    """Filter out private and model_exclude memories from MCP responses."""
    if include_private:
        return memories
    return [
        m
        for m in memories
        if not _flag_enabled(getattr(m, "is_private", False))
        and not _flag_enabled(getattr(m, "model_exclude", False))
    ]


def _memory_to_dict(m: Any) -> dict[str, Any]:
    """Convert a Memory object to a serializable dict."""
    return {
        "id": m.id,
        "title": m.title,
        "content": str(m.content)[:500] if m.content else "",
        "memory_type": m.memory_type.name
        if hasattr(m.memory_type, "name")
        else str(m.memory_type),
        "importance": m.importance,
        "neuro_score": getattr(m, "neuro_score", 1.0),
        "novelty_score": getattr(m, "novelty_score", 1.0),
        "tags": list(m.tags) if m.tags else [],
        "created_at": m.created_at.isoformat()
        if hasattr(m.created_at, "isoformat")
        else str(m.created_at),
        "galactic_distance": getattr(m, "galactic_distance", None),
    }


def _detect_mode(query: str, **kwargs: Any) -> str:
    """Auto-detect the best read strategy based on query characteristics."""
    # STRATA analysis: path provided with strata flag
    if kwargs.get("path") and kwargs.get("strata"):
        return "strata"

    # Explicit path for codebase search
    if kwargs.get("path"):
        return "codebase"

    # ID lookup: query looks like a memory ID
    if query.startswith("mem_") and len(query) < 64 and " " not in query:
        return "id"

    # Constellation query: tags or coords provided without a text query
    if not query and (kwargs.get("tags") or kwargs.get("coords")):
        return "constellation"

    # Temporal query: no query string, time_window provided
    if not query and kwargs.get("time_window"):
        return "temporal"

    # Spatial query: coords provided with a query
    if kwargs.get("coords"):
        return "spatial"

    # Default: hybrid recall (the most powerful general-purpose strategy)
    return "hybrid"


def handle_wm_read(**kwargs: Any) -> dict[str, Any]:
    """Unified read interface — auto-selects best strategy or uses explicit mode.

    Args (via kwargs):
        query: Search query text or memory ID
        mode: Read strategy (auto, hybrid, graph_walk, semantic, lexical,
              spatial, constellation, temporal, codebase, id)
        limit: Maximum results (default 10)
        include_private: Include private memories in results (default False)
        include_cold: Search cold storage / archived memories (default False)

        # Mode-specific:
        path: Codebase path for codebase mode
        tags: List of tags for constellation mode
        coords: 5D coordinates tuple for spatial mode
        time_window: Time window string (e.g. "7d", "30d") for temporal mode
        hops: Graph walk depth for graph_walk mode (default 2)
        bucket: Bucket granularity for temporal mode (default "1d")

    Returns:
        Standard dispatch envelope with results and strategy metadata.
    """
    query = kwargs.get("query", "")
    mode = kwargs.get("mode", "auto")
    limit = int(kwargs.get("limit", 10))
    include_private = kwargs.get("include_private", False)
    include_cold = kwargs.get("include_cold", False)

    if mode == "auto":
        # Build detection kwargs without 'query' (already extracted) and 'mode'
        detect_kwargs = {k: v for k, v in kwargs.items() if k not in ("query", "mode")}
        mode = _detect_mode(query, **detect_kwargs)

    try:
        if mode == "id":
            result = _read_by_id(query, include_private)
        elif mode == "hybrid":
            result = _read_hybrid(query, limit, include_cold, include_private)
        elif mode == "graph_walk":
            result = _read_graph_walk(
                query, limit, include_cold, include_private, kwargs
            )
        elif mode == "semantic":
            result = _read_semantic(query, limit, include_cold, include_private)
        elif mode == "lexical":
            result = _read_lexical(query, limit, include_private)
        elif mode == "spatial":
            result = _read_spatial(kwargs, limit, include_private)
        elif mode == "constellation":
            result = _read_constellation(kwargs, limit)
        elif mode == "temporal":
            result = _read_temporal(kwargs)
        elif mode == "codebase":
            result = _read_codebase(query, kwargs, limit)
        elif mode == "strata":
            result = _read_strata(query, kwargs, limit)
        else:
            return {
                "status": "error",
                "error": f"Unknown read mode: {mode}",
                "available_modes": [
                    "auto",
                    "hybrid",
                    "graph_walk",
                    "semantic",
                    "lexical",
                    "spatial",
                    "constellation",
                    "temporal",
                    "codebase",
                    "strata",
                    "id",
                ],
            }

        # v23.1 Harmonic: attend read results into WorkingMemory
        if isinstance(result, dict) and result.get("status") == "success":
            try:
                from whitemagic.core.intelligence.working_memory import (
                    get_working_memory,
                )

                wm = get_working_memory()
                for entry in (result.get("results") or [])[:3]:
                    mid = entry.get("memory_id") or entry.get("id") or ""
                    content = (
                        entry.get("content")
                        or entry.get("preview")
                        or entry.get("analysis")
                        or ""
                    )
                    if mid and content:
                        wm.attend(
                            memory_id=str(mid),
                            content=str(content)[:500],
                            title=str(entry.get("title", ""))[:100],
                            importance=float(entry.get("importance", 0.5)),
                            tags=["wm_read", mode],
                        )
            except Exception:
                logger.debug("Ignored Exception in wm_read.py:204")

        return result
    except Exception as exc:
        logger.error("wm_read failed (mode=%s): %s", mode, exc, exc_info=True)
        return {
            "status": "error",
            "error": str(exc),
            "mode": mode,
            "query": query,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Mode Implementations
# ═══════════════════════════════════════════════════════════════════════════════


def _read_by_id(query: str, include_private: bool) -> dict[str, Any]:
    """Direct memory recall by ID with galactic promotion."""
    from whitemagic.core.memory.unified import get_unified_memory

    mem = get_unified_memory()
    memory = mem.recall(query)
    if memory is None:
        return {
            "status": "success",
            "mode": "id",
            "count": 0,
            "results": [],
            "note": f"No memory found with id={query}",
        }
    if not include_private and (
        _flag_enabled(getattr(memory, "is_private", False))
        or _flag_enabled(getattr(memory, "model_exclude", False))
    ):
        return {
            "status": "success",
            "mode": "id",
            "count": 0,
            "results": [],
            "note": "Memory exists but is private/excluded",
        }
    return {
        "status": "success",
        "mode": "id",
        "count": 1,
        "results": [_memory_to_dict(memory)],
    }


def _read_hybrid(
    query: str, limit: int, include_cold: bool, include_private: bool
) -> dict[str, Any]:
    """Vector + graph RRF fusion via CoreAccessLayer.

    Auto-fallback to cold storage when hot results are insufficient (v23.1).
    """
    from whitemagic.core.intelligence.core_access import get_core_access

    cal = get_core_access()
    results = cal.hybrid_recall(query, k=limit, include_cold=include_cold)

    # Transparent cold storage fallback: if hot results are insufficient,
    # automatically retry with cold storage included
    cold_fallback_used = False
    if not include_cold and len(results) < limit:
        try:
            cold_results = cal.hybrid_recall(query, k=limit, include_cold=True)
            if len(cold_results) > len(results):
                results = cold_results
                cold_fallback_used = True
        except Exception:
            logger.debug("Ignored Exception in wm_read.py:277")

    # Hydrate full memory data for each result
    hydrated = []
    for r in results:
        entry = r.to_dict()
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            mem = get_unified_memory().recall(r.memory_id)
            if mem and (
                include_private
                or (
                    not _flag_enabled(getattr(mem, "is_private", False))
                    and not _flag_enabled(getattr(mem, "model_exclude", False))
                )
            ):
                entry["memory_type"] = (
                    mem.memory_type.name
                    if hasattr(mem.memory_type, "name")
                    else str(mem.memory_type)
                )
                entry["importance"] = mem.importance
                entry["neuro_score"] = getattr(mem, "neuro_score", 1.0)
                entry["tags"] = list(mem.tags) if mem.tags else []
                entry["galactic_distance"] = getattr(mem, "galactic_distance", None)
                hydrated.append(entry)
            elif include_private:
                hydrated.append(entry)
        except Exception:
            hydrated.append(entry)

    return {
        "status": "success",
        "mode": "hybrid",
        "query": query,
        "count": len(hydrated),
        "results": hydrated[:limit],
        "strategy": "vector + graph RRF (Reciprocal Rank Fusion)",
        "include_cold": include_cold or cold_fallback_used,
        "cold_fallback": cold_fallback_used,
    }


def _read_graph_walk(
    query: str,
    limit: int,
    include_cold: bool,
    include_private: bool,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Anchor search + multi-hop graph walk via GraphWalker."""
    hops = int(kwargs.get("hops", 2))
    anchor_limit = int(kwargs.get("anchor_limit", 5))

    try:
        from whitemagic.core.memory.graph_walker import get_graph_walker

        walker = get_graph_walker()
        results = walker.hybrid_recall(
            query=query,
            hops=hops,
            anchor_limit=anchor_limit,
            final_limit=limit,
        )
        return {
            "status": "success",
            "mode": "graph_walk",
            "query": query,
            "count": len(results),
            "results": results[:limit],
            "strategy": f"anchor search + {hops}-hop graph walk",
            "hops": hops,
        }
    except Exception as exc:
        logger.debug("graph_walk failed, falling back to hybrid: %s", exc)
        return _read_hybrid(query, limit, include_cold, include_private)


def _read_semantic(
    query: str, limit: int, include_cold: bool, include_private: bool
) -> dict[str, Any]:
    """Embedding similarity search via EmbeddingEngine."""
    from whitemagic.core.memory.embeddings import get_embedding_engine

    engine = get_embedding_engine()
    hits = engine.search_similar(query, limit=limit, include_cold=include_cold)

    results = []
    for hit in hits:
        mid = hit.get("memory_id") or hit.get("id", "")
        entry = {
            "memory_id": mid,
            "title": hit.get("title"),
            "content_preview": hit.get("content", "")[:200]
            if hit.get("content")
            else "",
            "similarity": hit.get("similarity", 0.0),
            "sources": ["vector"],
        }
        # Hydrate with full memory if available
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            mem = get_unified_memory().recall(mid)
            if mem and (
                include_private
                or (
                    not _flag_enabled(getattr(mem, "is_private", False))
                    and not _flag_enabled(getattr(mem, "model_exclude", False))
                )
            ):
                entry["memory_type"] = (
                    mem.memory_type.name
                    if hasattr(mem.memory_type, "name")
                    else str(mem.memory_type)
                )
                entry["importance"] = mem.importance
                entry["tags"] = list(mem.tags) if mem.tags else []
                entry["galactic_distance"] = getattr(mem, "galactic_distance", None)
                results.append(entry)
        except Exception:
            results.append(entry)

    return {
        "status": "success",
        "mode": "semantic",
        "query": query,
        "count": len(results),
        "results": results[:limit],
        "strategy": "MiniLM-L6-v2 embedding similarity (HNSW)",
        "include_cold": include_cold,
    }


def _read_lexical(query: str, limit: int, include_private: bool) -> dict[str, Any]:
    """FTS5 BM25 full-text search via UnifiedMemory."""
    from whitemagic.core.memory.unified import get_unified_memory

    mem = get_unified_memory()
    memories = mem.search(query=query, limit=limit)
    memories = _filter_private(memories, include_private)

    return {
        "status": "success",
        "mode": "lexical",
        "query": query,
        "count": len(memories),
        "results": [_memory_to_dict(m) for m in memories[:limit]],
        "strategy": "FTS5 BM25 full-text search",
    }


def _read_spatial(
    kwargs: dict[str, Any], limit: int, include_private: bool
) -> dict[str, Any]:
    """5D holographic KNN via CoreAccessLayer."""
    from whitemagic.core.intelligence.core_access import get_core_access

    cal = get_core_access()
    coords = kwargs.get("coords")
    if not coords or len(coords) != 5:
        return {
            "status": "error",
            "error": "spatial mode requires coords (tuple of 5 floats: x, y, z, w, v)",
        }

    neighbors = cal.query_holographic_neighbors(
        coords=tuple(coords),
        k=limit,
        include_cold=kwargs.get("include_cold", False),
    )

    return {
        "status": "success",
        "mode": "spatial",
        "count": len(neighbors),
        "results": [n.to_dict() for n in neighbors],
        "strategy": "5D holographic KNN (Euclidean distance in coordinate space)",
        "coords": {
            "x": coords[0],
            "y": coords[1],
            "z": coords[2],
            "w": coords[3],
            "v": coords[4],
        },
    }


def _read_constellation(kwargs: dict[str, Any], limit: int) -> dict[str, Any]:
    """Constellation context query via CoreAccessLayer."""
    from whitemagic.core.intelligence.core_access import get_core_access

    cal = get_core_access()
    tags = kwargs.get("tags")
    coords = kwargs.get("coords")

    constellations = cal.query_constellation_context(tags=tags, coords=coords, k=limit)

    return {
        "status": "success",
        "mode": "constellation",
        "count": len(constellations),
        "results": [c.to_dict() for c in constellations],
        "strategy": "Constellation tag/coordinate matching",
        "query_tags": tags,
    }


def _read_temporal(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Time-bucketed activity metrics via CoreAccessLayer."""
    from whitemagic.core.intelligence.core_access import get_core_access

    cal = get_core_access()
    time_window = kwargs.get("time_window", "7d")
    bucket = kwargs.get("bucket", "1d")

    buckets = cal.query_temporal_activity(time_window=time_window, bucket=bucket)
    velocity = cal.get_velocity_metrics()

    return {
        "status": "success",
        "mode": "temporal",
        "count": len(buckets),
        "results": [b.to_dict() for b in buckets],
        "velocity": velocity,
        "strategy": f"Time-bucketed activity ({time_window} window, {bucket} buckets)",
    }


def _read_codebase(query: str, kwargs: dict[str, Any], limit: int) -> dict[str, Any]:
    """Fragment (Rust) accelerated codebase search."""
    path = kwargs.get("path")
    if not path:
        return {
            "status": "error",
            "error": "codebase mode requires a 'path' parameter pointing to the codebase root",
        }

    try:
        from whitemagic.tools.handlers.fragment import fragment_accelerated_search

        accel = fragment_accelerated_search(query, path=path, top=limit)
        if accel is not None:
            return {
                "status": "success",
                "mode": "codebase",
                "query": query,
                "path": path,
                "count": accel["count"],
                "results": accel["results"],
                "accelerated": True,
                "layer": accel["layer"],
                "strategy": "Fragment (Rust) BM25 + semantic codebase search",
            }
    except Exception as exc:
        logger.debug("Fragment acceleration failed: %s", exc)

    # Fallback to vector search with codebase path
    try:
        from whitemagic.tools.handlers.vector_search import handle_vector_search

        result = handle_vector_search(query=query, path=path, limit=limit)
        if result.get("status") == "success":
            result["mode"] = "codebase"
            result["strategy"] = "Python vector search (Fragment unavailable)"
            return result
    except Exception as exc:
        logger.debug("Vector search fallback failed: %s", exc)

    return {
        "status": "success",
        "mode": "codebase",
        "query": query,
        "path": path,
        "count": 0,
        "results": [],
        "accelerated": False,
        "note": "No codebase search backend available (Fragment and vector search both unavailable)",
    }


def _read_strata(query: str, kwargs: dict[str, Any], limit: int) -> dict[str, Any]:
    """STRATA static analysis — 80+ checkers across 15 languages."""
    path = kwargs.get("path")
    if not path:
        return {
            "status": "error",
            "error": "strata mode requires a 'path' parameter pointing to the codebase root",
        }

    try:
        from whitemagic.tools.handlers.strata import handle_strata_analyze

        result = handle_strata_analyze(
            path=path,
            format=kwargs.get("format", "json"),
            parallel=kwargs.get("parallel", False),
            incremental=kwargs.get("incremental", True),
            disable=kwargs.get("disable", []),
            context=kwargs.get("context", False),
            since_ref=kwargs.get("since_ref"),
            diff_base=kwargs.get("diff_base"),
        )
        result["mode"] = "strata"
        result["strategy"] = "STRATA static analysis (80+ checkers)"
        return result
    except Exception as exc:
        logger.debug("STRATA analysis failed: %s", exc)
        return {
            "status": "error",
            "error": str(exc),
            "mode": "strata",
            "path": path,
        }


def handle_wm_read_status(**kwargs: Any) -> dict[str, Any]:
    """Get wm_read system status — available modes, backend availability, and stats."""
    status: dict[str, Any] = {
        "status": "success",
        "modes": [
            "auto",
            "hybrid",
            "graph_walk",
            "semantic",
            "lexical",
            "spatial",
            "constellation",
            "temporal",
            "codebase",
            "strata",
            "id",
        ],
        "backends": {},
    }

    try:
        from whitemagic.core.intelligence.core_access import get_core_access

        cal = get_core_access()
        status["backends"]["core_access"] = "available"
        status["association_stats"] = cal.get_association_stats()
        status["velocity"] = cal.get_velocity_metrics()
    except Exception:
        status["backends"]["core_access"] = "unavailable"

    try:
        from whitemagic.core.memory.embeddings import get_embedding_engine

        engine = get_embedding_engine()
        status["backends"]["embedding_engine"] = (
            "available" if engine._model is not None else "lazy_loaded"
        )
    except Exception:
        status["backends"]["embedding_engine"] = "unavailable"

    try:
        from whitemagic.core.memory.graph_walker import get_graph_walker

        get_graph_walker()
        status["backends"]["graph_walker"] = "available"
    except Exception:
        status["backends"]["graph_walker"] = "unavailable"

    try:
        from whitemagic.tools.handlers.fragment import _get_pyo3

        pyo3 = _get_pyo3()
        status["backends"]["fragment"] = "pyo3" if pyo3 else "unavailable"
    except Exception:
        status["backends"]["fragment"] = "unavailable"

    try:
        from whitemagic.core.memory.unified import get_unified_memory

        mem = get_unified_memory()
        status["backends"]["unified_memory"] = "available"
        status["memory_count"] = (
            mem.count() if hasattr(mem.backend, "count") else None
        )
    except Exception:
        status["backends"]["unified_memory"] = "unavailable"

    return status
