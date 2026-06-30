"""Meta-Tool Registry Definition — 'World in a Seed'.

The ``wm`` meta-tool is a single facade that auto-routes natural language
to the appropriate Gana + sub-tool. When WM_MCP_PRAT=2, only this tool
is registered with MCP.

Special modes:
    - wm(thought='help') or wm(route='discover') → full Gana catalog
    - wm(route='schema:gana_name') → nested tools for a specific Gana
"""

from whitemagic.tools.tool_types import (
    ToolCategory,
    ToolDefinition,
    ToolSafety,
    ToolStability,
)

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="wm",
        description=(
            "[WM] WhiteMagic meta-tool — single entry point that auto-routes "
            "natural language to 28 Ganas / 490 tools. 'World in a seed'. "
            "Use for any WhiteMagic operation without knowing the specific tool name. "
            "Supports explicit route= override (e.g. route='gana_neck.create_memory'). "
            "Use thought='help' or route='discover' to see all Ganas and their tools. "
            "Use route='schema:gana_name' to get a Gana's nested tool list."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "Natural language describing what you want to do. Use 'help' to discover all capabilities.",
                },
                "route": {
                    "type": "string",
                    "description": "Explicit route: 'gana_name.sub_tool', 'discover', or 'schema:gana_name'.",
                },
                "args": {
                    "type": "object",
                    "description": "Args dict to pass through to the target tool.",
                },
            },
        },
        stability=ToolStability.STABLE,
    ),
]
