"""Immune & DNA Tools — validate fixes against core principles, list principles.
"""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
ToolDefinition(
    name="dna_validate",
    description=(
        "Validate a proposed fix against WhiteMagic's core DNA principles. "
        "Checks for violations of immutable principles (no self-destruction, "
        "memory integrity, reversibility, test before deploy). "
        "Returns safe/violation status and suppression recommendation."
    ),
    category=ToolCategory.SYSTEM,
    safety=ToolSafety.READ,
    input_schema={
        "type": "object",
        "properties": {
            "fix_details": {
                "type": "object",
                "description": "Dict with 'action' and 'file' keys describing the proposed fix",
                "properties": {
                    "action": {"type": "string", "description": "Action being taken (e.g. 'delete file', 'update version')"},
                    "file": {"type": "string", "description": "File path being modified"},
                },
            },
            "threat_type": {"type": "string", "description": "Type of threat being addressed", "default": "unknown"},
            "recent_failures": {"type": "integer", "description": "Number of recent failed responses (for suppression logic)", "default": 0},
        },
        "required": ["fix_details"],
    },
),
ToolDefinition(
    name="dna_principles",
    description="List all core DNA principles that govern WhiteMagic's immune system",
    category=ToolCategory.INTROSPECTION,
    safety=ToolSafety.READ,
    input_schema={"type": "object", "properties": {}},
),
]
