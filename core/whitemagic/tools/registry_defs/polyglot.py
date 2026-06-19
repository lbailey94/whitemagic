"""Polyglot Memory Tools — Route holographic memory queries to Julia/Elixir/Haskell/Rust backends.
"""

from whitemagic.tools.tool_types import (
    ToolCategory,
    ToolDefinition,
    ToolSafety,
    ToolStability,
)

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="polyglot.memory_query",
        description=(
            "Execute a holographic memory query through an available polyglot backend "
            "(Julia, Elixir, Haskell, or Rust). Supports encode, nearest_neighbors, "
            "constellation_detect, and coherence_score. Falls back through backends "
            "automatically if one is unavailable."
        ),
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["encode", "nearest_neighbors", "constellation_detect", "coherence_score"],
                    "description": "Holographic memory operation to execute",
                },
                "text": {
                    "type": "string",
                    "description": "Text to encode (for encode operation)",
                },
                "query": {
                    "type": "string",
                    "description": "Query text (for nearest_neighbors)",
                },
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of texts to search against (for nearest_neighbors)",
                },
                "coords": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                    "description": "List of 5D coordinates (for constellation_detect, coherence_score)",
                },
                "k": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of nearest neighbors to return",
                },
                "backend": {
                    "type": "string",
                    "enum": ["auto", "julia", "elixir", "haskell", "rust"],
                    "default": "auto",
                    "description": "Backend to use (auto = first available)",
                },
            },
            "required": ["operation"],
        },
        gana="Mound",
        garden="metrics",
        quadrant="western",
        element="metal",
        stability=ToolStability.EXPERIMENTAL,
    ),
    ToolDefinition(
        name="polyglot.search",
        description=(
            "Convenience tool: encode a query text and find its nearest neighbors "
            "among a pool of texts in a single call. Routes through polyglot backend."
        ),
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query text to encode"},
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Pool of texts to search against",
                },
                "k": {"type": "integer", "default": 5, "description": "Number of results"},
                "backend": {
                    "type": "string",
                    "enum": ["auto", "julia", "elixir", "haskell", "rust"],
                    "default": "auto",
                    "description": "Backend to use",
                },
            },
            "required": ["query", "texts"],
        },
        gana="WinnowingBasket",
        garden="metrics",
        quadrant="western",
        element="metal",
        stability=ToolStability.EXPERIMENTAL,
    ),
    ToolDefinition(
        name="polyglot.status",
        description=(
            "Check availability and health of all polyglot holographic memory backends. "
            "Returns per-backend ping results and an overall health score."
        ),
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        gana="Ghost",
        garden="introspection",
        quadrant="southern",
        element="fire",
        stability=ToolStability.EXPERIMENTAL,
    ),
]
