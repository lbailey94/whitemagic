# ruff: noqa: BLE001
"""Living Graph handlers — Graph topology and analysis."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Graph Topology
# ═══════════════════════════════════════════════════════════════════════════════

def handle_graph_topology(**kwargs: Any) -> dict[str, Any]:
    """Get graph topology statistics."""
    try:
        from whitemagic.core.intelligence.graph_engine import GraphEngine

        engine = GraphEngine()
        stats = engine.get_topology_stats()

        return {
            "status": "success",
            "topology": {
                "nodes": stats.get("node_count", 0),
                "edges": stats.get("edge_count", 0),
                "communities": stats.get("community_count", 0),
                "density": stats.get("density", 0.0),
                "avg_degree": stats.get("avg_degree", 0.0),
            }
        }
    except ImportError:
        return {
            "status": "success",
            "topology": {
                "nodes": 0,
                "edges": 0,
                "communities": 0,
                "density": 0.0,
                "avg_degree": 0.0,
            },
            "note": "GraphEngine archived - no topology data available"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Community Operations
# ═══════════════════════════════════════════════════════════════════════════════

def handle_community_propagate(**kwargs: Any) -> dict[str, Any]:
    """Propagate information through graph communities."""
    try:
        from whitemagic.core.intelligence.graph_engine import GraphEngine

        engine = GraphEngine()
        message = kwargs.get("message", "")
        community_id = kwargs.get("community_id")

        result = engine.propagate_in_community(community_id, message)
        return {"status": "success", "propagated": result}
    except ImportError:
        return {
            "status": "success",
            "propagated": False,
            "note": "GraphEngine archived - propagation not available"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_community_status(**kwargs: Any) -> dict[str, Any]:
    """Get community health status."""
    try:
        from whitemagic.core.intelligence.graph_engine import GraphEngine

        engine = GraphEngine()
        communities = engine.get_communities()

        return {
            "status": "success",
            "community_count": len(communities),
            "communities": communities[:10]
        }
    except ImportError:
        return {
            "status": "success",
            "community_count": 0,
            "communities": [],
            "note": "GraphEngine archived - no community data available"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_community_health(**kwargs: Any) -> dict[str, Any]:
    """Analyze community health metrics."""
    try:
        from whitemagic.core.intelligence.graph_engine import GraphEngine

        engine = GraphEngine()
        health = engine.analyze_community_health()

        return {"status": "success", "health": health}
    except ImportError:
        return {
            "status": "success",
            "health": {},
            "note": "GraphEngine archived - health analysis not available"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Hybrid Recall
# ═══════════════════════════════════════════════════════════════════════════════

def handle_hybrid_recall(**kwargs: Any) -> dict[str, Any]:
    """Perform hybrid recall combining FTS, vector, and graph search.

    When a codebase path is provided, tries Fragment (Rust) hybrid search first
    for 100x faster BM25+semantic codebase retrieval. Falls back to Python.

    Rust PyO3 acceleration: uses search_build_index + search_query for BM25
    ranking when available, falling back to Python SQLite FTS.
    """
    query = kwargs.get("query", "")
    limit = kwargs.get("limit", kwargs.get("top_k", 10))
    path = kwargs.get("path")

    if not query:
        return {"status": "error", "error": "query required"}

    # Fragment acceleration for codebase search
    if path:
        try:
            from whitemagic.tools.handlers.fragment import fragment_accelerated_search
            accel = fragment_accelerated_search(query, path=path, top=int(limit))
            if accel is not None:
                return {
                    "status": "success",
                    "query": query,
                    "results_count": accel["count"],
                    "results": accel["results"],
                    "accelerated": True,
                    "layer": accel["layer"],
                }
        except Exception:
            pass  # Fall through to Python

    # Rust PyO3 BM25 fast path
    try:
        import whitemagic_rs
        from whitemagic.core.memory.unified import get_unified_memory

        mem = get_unified_memory()
        # Get candidates from Python backend (FTS + filters)
        candidates = mem.backend.search(query=None, limit=max(limit * 5, 50))
        if candidates and len(candidates) > 0:
            # Build Rust search index from candidates
            docs = [
                {"id": c.id, "title": c.title or "", "content": str(c.content)[:500]}
                for c in candidates
            ]
            import json as _json
            whitemagic_rs.search_build_index(_json.dumps(docs))
            raw_results = whitemagic_rs.search_query(query, int(limit))

            # Rust search_query returns a JSON string — parse it
            if isinstance(raw_results, str):
                rust_results = _json.loads(raw_results)
            else:
                rust_results = raw_results

            if rust_results:
                # Map back to full Memory objects
                candidate_map = {c.id: c for c in candidates}
                results = []
                for r in rust_results:
                    rid = r.get("id", "")
                    if rid in candidate_map:
                        mem_obj = candidate_map[rid]
                        results.append({
                            "id": mem_obj.id,
                            "content": mem_obj.content,
                            "title": mem_obj.title,
                            "created_at": mem_obj.created_at.isoformat() if hasattr(mem_obj.created_at, 'isoformat') else str(mem_obj.created_at),
                            "tags": list(mem_obj.tags) if mem_obj.tags else [],
                            "importance": mem_obj.importance,
                            "neuro_score": mem_obj.neuro_score,
                            "novelty_score": mem_obj.novelty_score,
                            "recall_count": mem_obj.recall_count,
                            "metadata": {"bm25_score": r.get("score", 0.0)},
                        })
                if results:
                    return {
                        "status": "success",
                        "query": query,
                        "results_count": len(results),
                        "results": results,
                        "accelerated": True,
                        "engine": "rust_bm25",
                    }
    except Exception:
        pass  # Fall through to Python

    try:
        from whitemagic.core.intelligence.core_access import get_core_access
        cal = get_core_access()
        results = cal.hybrid_recall(
            query=query,
            k=limit,
            include_cold=bool(kwargs.get("include_cold", False)),
        )
        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "results": [r.to_dict() for r in results],
            "strategy": "vector + graph RRF (CoreAccessLayer)",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Graph Walk & Surprise Stats
# ═══════════════════════════════════════════════════════════════════════════════

def handle_graph_walk(**kwargs: Any) -> dict[str, Any]:
    """Walk the knowledge graph from a starting node."""
    try:
        from whitemagic.core.intelligence.graph_engine import GraphEngine

        start_node = kwargs.get("start_node")
        steps = kwargs.get("steps", 10)

        if not start_node:
            return {"status": "error", "error": "start_node required"}

        engine = GraphEngine()
        path = engine.graph_walk(start=start_node, steps=steps)

        return {
            "status": "success",
            "start_node": start_node,
            "steps": steps,
            "path": path
        }
    except ImportError:
        return {
            "status": "success",
            "start_node": kwargs.get("start_node"),
            "steps": kwargs.get("steps", 10),
            "path": [],
            "note": "GraphEngine archived - graph walk not available"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_surprise_stats(**kwargs: Any) -> dict[str, Any]:
    """Get surprise detection statistics."""
    try:
        from whitemagic.core.intelligence.surprise import SurpriseDetector
        detector = SurpriseDetector()
        return {
            "status": "success",
            **detector.get_stats()
        }
    except ImportError:
        return {
            "status": "success",
            "surprise_events": 0,
            "average_surprise": 0.0,
            "note": "Surprise detector archived"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_entity_resolve(**kwargs: Any) -> dict[str, Any]:
    """Resolve entity mentions to canonical entities."""
    try:
        from whitemagic.core.intelligence.entity_resolver import EntityResolver
        resolver = EntityResolver()

        mentions = kwargs.get("mentions", [])
        context = kwargs.get("context", {})

        if not mentions:
            return {"status": "error", "error": "mentions required"}

        resolved = resolver.resolve(mentions=mentions, context=context)
        return {
            "status": "success",
            "mentions": len(mentions),
            "resolved": resolved
        }
    except ImportError:
        return {
            "status": "success",
            "mentions": len(kwargs.get("mentions", [])),
            "resolved": {},
            "note": "Entity resolver archived"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
