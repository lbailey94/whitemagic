"""MCP handlers for Knowledge Graph Extraction."""

from typing import Any


def handle_kg_extract(**kwargs: Any) -> dict[str, Any]:
    """Extract entities and relations from text into the knowledge graph."""
    from whitemagic.core.intelligence.knowledge_graph import get_knowledge_graph
    source_id = kwargs.get("source_id", "")
    text = kwargs.get("text", "")
    if not text:
        return {"status": "error", "error": "text is required"}
    kg = get_knowledge_graph()
    result = kg.extract_from_text(source_id or "manual", text)
    return {"status": "success", **result}


def handle_kg_query(**kwargs: Any) -> dict[str, Any]:
    """Query an entity and its connections in the knowledge graph."""
    from whitemagic.core.intelligence.knowledge_graph import get_knowledge_graph
    name = kwargs.get("name", "")
    if not name:
        return {"status": "error", "error": "name is required"}
    kg = get_knowledge_graph()
    return {"status": "success", **kg.query_entity(name)}


def handle_kg_top(**kwargs: Any) -> dict[str, Any]:
    """Get top entities by mention count."""
    from whitemagic.core.intelligence.knowledge_graph import get_knowledge_graph
    limit = int(kwargs.get("limit", 20))
    kg = get_knowledge_graph()
    return {"status": "success", "entities": kg.top_entities(limit=limit)}


def handle_kg_status(**kwargs: Any) -> dict[str, Any]:
    """Get knowledge graph status."""
    from whitemagic.core.intelligence.knowledge_graph import get_knowledge_graph
    kg = get_knowledge_graph()
    return {"status": "success", **kg.status()}


# v16: Knowledge Graph 2.0 with LightNER

def handle_kg2_extract(**kwargs: Any) -> dict[str, Any]:
    """Extract entities and relations using LightNER (fast pattern-based)."""
    from whitemagic.core.intelligence.knowledge_graph_v2 import get_kg_v2
    source_id = kwargs.get("source_id", "manual")
    text = kwargs.get("text", "")
    if not text:
        return {"status": "error", "error": "text is required"}
    kg = get_kg_v2()
    result = kg.extract_and_store(source_id, text)
    return {"status": "success", **result}


def handle_kg2_batch(**kwargs: Any) -> dict[str, Any]:
    """Batch extract from multiple memories."""
    from whitemagic.core.intelligence.knowledge_graph_v2 import get_kg_v2
    limit = int(kwargs.get("limit", 100))
    kg = get_kg_v2()
    result = kg.process_unextracted_memories(limit=limit)
    return {"status": "success", **result}


def handle_kg2_entity(**kwargs: Any) -> dict[str, Any]:
    """Query entity graph with typed edges."""
    from whitemagic.core.intelligence.knowledge_graph_v2 import get_kg_v2
    name = kwargs.get("name", "")
    if not name:
        return {"status": "error", "error": "name is required"}
    kg = get_kg_v2()
    return {"status": "success", **kg.get_entity_graph(name)}


def handle_kg2_stats(**kwargs: Any) -> dict[str, Any]:
    """Get KG2 extraction statistics."""
    from whitemagic.core.intelligence.knowledge_graph_v2 import get_kg_v2
    kg = get_kg_v2()
    return {"status": "success", **kg.get_stats()}


# v16: Embedding Daemon

def handle_embedding_daemon_start(**kwargs: Any) -> dict[str, Any]:
    """Start the background embedding daemon."""
    from whitemagic.core.memory.embedding_daemon import get_embedding_daemon
    daemon = get_embedding_daemon()
    daemon.start()
    return {"status": "success", "running": daemon._stats.is_running}


def handle_embedding_daemon_stop(**kwargs: Any) -> dict[str, Any]:
    """Stop the embedding daemon."""
    from whitemagic.core.memory.embedding_daemon import get_embedding_daemon
    daemon = get_embedding_daemon()
    daemon.stop()
    return {"status": "success", "running": False}


def handle_embedding_daemon_status(**kwargs: Any) -> dict[str, Any]:
    """Get embedding daemon status."""
    from whitemagic.core.memory.embedding_daemon import get_embedding_daemon
    daemon = get_embedding_daemon()
    return {"status": "success", **daemon.get_stats()}


def handle_embedding_daemon_process(**kwargs: Any) -> dict[str, Any]:
    """Process embeddings immediately (blocking)."""
    from whitemagic.core.memory.embedding_daemon import get_embedding_daemon
    limit = int(kwargs.get("limit", 100))
    daemon = get_embedding_daemon()
    result = daemon.process_now(limit=limit)
    return {"status": "success", **result}
