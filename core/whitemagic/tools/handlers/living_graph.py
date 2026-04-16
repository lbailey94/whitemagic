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
    """Perform hybrid recall combining FTS, vector, and graph search."""
    try:
        from whitemagic.core.memory.unified import get_unified_memory

        query = kwargs.get("query", "")
        limit = kwargs.get("limit", kwargs.get("top_k", 10))

        if not query:
            return {"status": "error", "error": "query required"}

        mem = get_unified_memory()
        # Use search() method which is the standard interface
        results = mem.search(query=query, limit=limit)

        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "results": results
        }
    except ImportError:
        return {
            "status": "success",
            "query": kwargs.get("query", ""),
            "results_count": 0,
            "results": [],
            "note": "Hybrid recall archived - use search_memories instead"
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
