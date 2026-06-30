"""Webhook trigger routes for mobile/remote tool invocation.

Optional FastAPI dependency — gracefully degrades when FastAPI is unavailable.
"""

from typing import Any

try:
    from fastapi import APIRouter, HTTPException

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = object  # type: ignore[misc,assignment]
    HTTPException = Exception  # type: ignore[misc,assignment]


# Whitelist of tools callable via webhook
ALLOWED_ACTIONS: dict[str, dict[str, Any]] = {
    "search_memories": {
        "description": "Search the memory system",
        "tool": "memory_search",
        "safety": "read",
    },
    "create_memory": {
        "description": "Store a new memory",
        "tool": "create_memory",
        "safety": "write",
    },
    "get_status": {
        "description": "Get system health status",
        "tool": "capabilities",
        "safety": "read",
    },
}


if HAS_FASTAPI:
    router = APIRouter(prefix="/webhooks", tags=["webhooks"])

    @router.post("/{action}")
    async def webhook_trigger(
        action: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a whitelisted tool via webhook."""
        if action not in ALLOWED_ACTIONS:
            raise HTTPException(
                status_code=404, detail=f"Action '{action}' not in whitelist"
            )

        config = ALLOWED_ACTIONS[action]
        from whitemagic.tools.unified_api import call_tool

        result = call_tool(config["tool"], **(payload or {}))
        return {
            "status": result.get("status", "unknown"),
            "action": action,
            "tool": config["tool"],
            "result": result,
        }
else:
    router = None  # type: ignore[assignment]
