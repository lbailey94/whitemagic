"""Knowledge Graph Fusion — KG entity relationships → Gana routing.

Use Knowledge Graph entity relationships to suggest which Gana to invoke next.
Extracted from fusions.py for better separation of concerns.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def kg_suggest_next_gana(current_tool: str) -> dict[str, Any]:
    """Use Knowledge Graph entity relationships to suggest which Gana
    to invoke next based on the current tool's KG connections.

    The KG knows which tools/concepts are related — if tool A creates
    entities that tool B typically queries, the KG can suggest B next.

    Args:
        current_tool: The tool that was just invoked.

    Returns:
        Dict with suggested next Ganas and reasoning.
    """
    try:
        from whitemagic.core.intelligence.knowledge_graph import get_knowledge_graph
        from whitemagic.tools.prat_router import TOOL_TO_GANA

        kg = get_knowledge_graph()

        # Find KG entities related to this tool
        relations = kg.query_entity(current_tool)
        if not relations:
            # Try with dots replaced (e.g. "memory.consolidate" → "memory consolidate")
            relations = kg.query_entity(current_tool.replace(".", " "))

        if not relations or not isinstance(relations, dict):
            return {"suggestions": [], "reason": "no KG relations for this tool"}

        # Extract related entity names
        related = set()
        for rel_list in relations.values():
            if isinstance(rel_list, list):
                for item in rel_list[:10]:
                    if isinstance(item, dict):
                        related.add(item.get("target", item.get("obj", "")))
                    elif isinstance(item, str):
                        related.add(item)

        # Map related entities to Ganas
        suggested_ganas = {}
        for entity in related:
            if not isinstance(entity, str):
                continue
            entity_lower = entity.lower().replace(" ", "_").replace(".", "_")
            # Check if the entity is a known tool
            if entity_lower in TOOL_TO_GANA:
                gana = TOOL_TO_GANA[entity_lower]
                if gana not in suggested_ganas:
                    suggested_ganas[gana] = {
                        "gana": gana,
                        "via_entity": entity,
                        "relation": "kg_associated",
                    }

        suggestions = list(suggested_ganas.values())[:5]

        return {
            "current_tool": current_tool,
            "kg_entities_found": len(related),
            "suggestions": suggestions,
        }

    except Exception as e:
        return {"suggestions": [], "error": str(e)}
