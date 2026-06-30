"""Unified Read API — Registry definitions for wm_read.

The unified read interface auto-selects the best search strategy based on
query characteristics, or delegates to an explicit mode. Covers all read
paths: lexical (FTS5), semantic (embedding), hybrid (RRF fusion),
graph walk, spatial (5D KNN), constellation, temporal, codebase (Fragment),
and direct ID recall.
"""

from whitemagic.tools.tool_types import (
    ToolCategory,
    ToolDefinition,
    ToolSafety,
    ToolStability,
)

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="wm_read",
        description=(
            "Unified read interface — auto-selects best strategy or uses explicit mode. "
            "Modes: auto, hybrid (vector+graph RRF), graph_walk, semantic, lexical, "
            "spatial (5D KNN), constellation, temporal, codebase (Fragment), "
            "strata (static analysis), id. "
            "Default mode 'auto' detects: mem_* → id, path present → codebase, "
            "coords present → spatial, tags without query → constellation, "
            "otherwise → hybrid."
        ),
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text or memory ID (e.g. 'mem_abc123')",
                },
                "mode": {
                    "type": "string",
                    "enum": [
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
                    "default": "auto",
                    "description": "Read strategy. 'auto' detects best strategy from query shape.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 10,
                },
                "include_private": {
                    "type": "boolean",
                    "description": "Include private/excluded memories in results",
                    "default": False,
                },
                "include_cold": {
                    "type": "boolean",
                    "description": "Search cold storage / archived memories",
                    "default": False,
                },
                "path": {
                    "type": "string",
                    "description": "Codebase path for codebase mode (Fragment/Rust acceleration)",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for constellation mode",
                },
                "coords": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 5,
                    "maxItems": 5,
                    "description": "5D holographic coordinates [x, y, z, w, v] for spatial mode",
                },
                "time_window": {
                    "type": "string",
                    "description": "Time window for temporal mode (e.g. '7d', '30d')",
                    "default": "7d",
                },
                "bucket": {
                    "type": "string",
                    "description": "Bucket granularity for temporal mode (e.g. '1d', '7d')",
                    "default": "1d",
                },
                "hops": {
                    "type": "integer",
                    "description": "Graph walk depth for graph_walk mode",
                    "default": 2,
                },
                "anchor_limit": {
                    "type": "integer",
                    "description": "Number of anchor results for graph_walk mode",
                    "default": 5,
                },
                "strata": {
                    "type": "boolean",
                    "description": "When True with path, auto-detects strata mode for static analysis",
                    "default": False,
                },
                "format": {
                    "type": "string",
                    "enum": ["json", "text", "sarif", "html"],
                    "description": "Output format for strata mode",
                    "default": "json",
                },
            },
        },
        stability=ToolStability.STABLE,
    ),
    ToolDefinition(
        name="wm_read.status",
        description="Get wm_read system status: available modes, backend availability, and stats.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        stability=ToolStability.STABLE,
    ),
]
