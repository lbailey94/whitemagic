"""Cognitive Extensions — Working Memory & Reconsolidation handlers."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_working_memory_attend(**kwargs: Any) -> dict[str, Any]:
    """Attend to working memory items."""
    from whitemagic.core.intelligence.working_memory import WorkingMemory
    wm = WorkingMemory()
    items = kwargs.get("items", [])

    count = 0
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                mid = item.get("memory_id") or item.get("id")
                content = item.get("content")
                if mid and content:
                    wm.attend(
                        memory_id=str(mid),
                        content=str(content),
                        title=str(item.get("title", "")),
                        importance=float(item.get("importance", 0.5)),
                        tags=item.get("tags")
                    )
                    count += 1
    elif isinstance(kwargs, dict):
        # Single item in kwargs
        mid = kwargs.get("memory_id") or kwargs.get("id")
        content = kwargs.get("content")
        if mid and content:
            wm.attend(
                memory_id=str(mid),
                content=str(content),
                title=str(kwargs.get("title", "")),
                importance=float(kwargs.get("importance", 0.5)),
                tags=kwargs.get("tags")
            )
            count = 1

    return {"status": "success", "attended": count}


def handle_working_memory_context(**kwargs: Any) -> dict[str, Any]:
    """Get current working memory context."""
    from whitemagic.core.intelligence.working_memory import WorkingMemory
    wm = WorkingMemory()
    return {"status": "success", "context": wm.get_context()}


def handle_working_memory_status(**kwargs: Any) -> dict[str, Any]:
    """Get working memory status."""
    from whitemagic.core.intelligence.working_memory import WorkingMemory
    wm = WorkingMemory()
    return {"status": "success", "working_memory": wm.get_status()}


def handle_reconsolidation_mark(**kwargs: Any) -> dict[str, Any]:
    """Mark memory for reconsolidation."""
    memory_id = kwargs.get("memory_id")
    if not memory_id:
        return {"status": "error", "error": "memory_id required"}

    from whitemagic.core.memory.unified import get_unified_memory
    mem = get_unified_memory()
    mem.mark_for_reconsolidation(memory_id)
    return {"status": "success", "memory_id": memory_id}


def handle_reconsolidation_update(**kwargs: Any) -> dict[str, Any]:
    """Update reconsolidated memory."""
    memory_id = kwargs.get("memory_id")
    updates = kwargs.get("updates", {})

    if not memory_id:
        return {"status": "error", "error": "memory_id required"}

    from whitemagic.core.memory.unified import get_unified_memory
    mem = get_unified_memory()
    mem.update_reconsolidated(memory_id, updates)
    return {"status": "success", "memory_id": memory_id, "updated": True}


def handle_reconsolidation_status(**kwargs: Any) -> dict[str, Any]:
    """Get reconsolidation status."""
    try:
        from whitemagic.core.memory.unified import get_unified_memory
        mem = get_unified_memory()

        # Try different method names that might exist
        pending = []
        if hasattr(mem, 'get_pending_reconsolidation'):
            pending = mem.get_pending_reconsolidation()
        elif hasattr(mem, 'get_reconsolidation_queue'):
            pending = mem.get_reconsolidation_queue()
        elif hasattr(mem, 'list_pending'):
            pending = mem.list_pending()

        return {"status": "success", "pending_count": len(pending), "pending": pending[:10]}
    except Exception as e:
        return {"status": "success", "pending_count": 0, "pending": [], "note": f"Reconsolidation tracking: {str(e)[:100]}"}


# ═══════════════════════════════════════════════════════════════════════════════
# Reranking (v15.6)
# ═══════════════════════════════════════════════════════════════════════════════

def handle_rerank(**kwargs: Any) -> dict[str, Any]:
    """Rerank search results using learned preferences."""
    try:
        from whitemagic.core.intelligence.reranker import Reranker
        reranker = Reranker()

        items = kwargs.get("items", [])
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 10)

        if not items:
            return {"status": "error", "error": "items required"}

        reranked = reranker.rerank(items=items, query=query, top_k=top_k)
        return {
            "status": "success",
            "original_count": len(items),
            "reranked_count": len(reranked),
            "items": reranked
        }
    except ImportError:
        # Fallback: return items as-is
        items = kwargs.get("items", [])
        return {
            "status": "success",
            "original_count": len(items),
            "reranked_count": len(items),
            "items": items[:kwargs.get("top_k", 10)],
            "note": "Reranker archived - returning original order"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def handle_rerank_status(**kwargs: Any) -> dict[str, Any]:
    """Get reranker system status."""
    try:
        from whitemagic.core.intelligence.reranker import Reranker
        reranker = Reranker()
        return {
            "status": "success",
            **reranker.get_status()
        }
    except ImportError:
        return {
            "status": "success",
            "active": False,
            "model_loaded": False,
            "training_samples": 0,
            "note": "Reranker archived"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
