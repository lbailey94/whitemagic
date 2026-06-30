"""Unified Write API — Registry definitions for wm_write.

The unified write interface auto-selects the best write backend based on
arguments, and ensures the full enrichment pipeline is applied for memory
writes (holographic coords, embeddings, entity extraction, surprise gate).
"""

from whitemagic.tools.tool_types import (
    ToolCategory,
    ToolDefinition,
    ToolSafety,
    ToolStability,
)

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="wm_write",
        description=(
            "Unified write interface — auto-selects best strategy or uses explicit mode. "
            "Modes: auto, memory (full enrichment), scratchpad (ephemeral), file (atomic), "
            "neural (neural store), dream (artifact), oms (.mem package). "
            "Memory mode enables: surprise gate, holographic coords, embeddings, "
            "entity extraction — unlike handle_create_memory which disables them."
        ),
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content to write (required)",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the content",
                },
                "mode": {
                    "type": "string",
                    "enum": [
                        "auto",
                        "memory",
                        "scratchpad",
                        "file",
                        "neural",
                        "dream",
                        "oms",
                    ],
                    "default": "auto",
                    "description": "Write strategy. 'auto' detects from args.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for memory mode",
                },
                "memory_type": {
                    "type": "string",
                    "enum": [
                        "short_term",
                        "long_term",
                        "emotional",
                        "narrative",
                        "symbolic",
                        "collective",
                        "immune",
                        "pattern",
                    ],
                    "default": "short_term",
                    "description": "Memory type for memory mode",
                },
                "importance": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5,
                    "description": "Importance score",
                },
                "emotional_valence": {
                    "type": "number",
                    "minimum": -1.0,
                    "maximum": 1.0,
                    "default": 0.0,
                    "description": "Emotional valence (-1 negative, +1 positive)",
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata",
                },
                "auto_embed": {
                    "type": "boolean",
                    "default": True,
                    "description": "Auto-generate embedding for memory mode",
                },
                "enable_surprise_gate": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable surprise-gated ingestion for memory mode",
                },
                "enable_entity_extraction": {
                    "type": "boolean",
                    "default": True,
                    "description": "Auto-extract entities for memory mode",
                },
                "enable_holographic_index": {
                    "type": "boolean",
                    "default": True,
                    "description": "Auto-compute 5D holographic coords for memory mode",
                },
                "is_private": {
                    "type": "boolean",
                    "default": False,
                    "description": "Mark as private (excluded from MCP responses)",
                },
                "model_exclude": {
                    "type": "boolean",
                    "default": False,
                    "description": "Exclude from AI model context windows",
                },
                "path": {
                    "type": "string",
                    "description": "File path for file mode",
                },
                "scratchpad_id": {
                    "type": "string",
                    "description": "Scratchpad ID for scratchpad mode",
                },
                "dream_type": {
                    "type": "string",
                    "description": "Dream artifact type for dream mode (e.g. 'bridge')",
                },
            },
            "required": ["content"],
        },
        stability=ToolStability.STABLE,
    ),
    ToolDefinition(
        name="wm_write.status",
        description="Get wm_write system status: available modes and backend availability.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
        stability=ToolStability.STABLE,
    ),
]
