"""STRATA Tools — Codebase static analysis and archaeology.

STRATA provides 80+ checkers across 15 languages, plus git history archaeology
(excavate, fossil, extinction, composition, temper).
Registered under Chariot (mobility & archaeology) in the PRAT system.
"""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="strata.analyze",
        description="Run STRATA static analysis on a codebase. 80+ checkers across 15 languages detecting structural stubs, dead code, archive drift, and more.",
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the codebase to analyze",
                },
                "incremental": {
                    "type": "boolean",
                    "default": True,
                    "description": "Only analyze changed files",
                },
                "severity": {
                    "type": "string",
                    "enum": ["error", "warning", "info"],
                    "description": "Minimum severity to report",
                },
            },
            "required": ["path"],
        },
    ),
    ToolDefinition(
        name="strata.survey",
        description="Fast surface survey of a codebase using file metadata and git history for quick summarization.",
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the codebase to survey",
                },
            },
            "required": ["path"],
        },
    ),
    ToolDefinition(
        name="strata.archaeology",
        description="Git history archaeology — excavate layers, find fossils, track extinctions, analyze composition, measure temper.",
        category=ToolCategory.ARCHAEOLOGY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the codebase"},
                "subcommand": {
                    "type": "string",
                    "enum": [
                        "excavate",
                        "fossil",
                        "extinction",
                        "composition",
                        "temper",
                    ],
                    "description": "Archaeology subcommand to run",
                },
                "top": {
                    "type": "integer",
                    "default": 10,
                    "description": "Top N results",
                },
                "layer": {
                    "type": "string",
                    "description": "Git layer/commit for excavate",
                },
                "file_path": {
                    "type": "string",
                    "description": "File filter for temper",
                },
            },
            "required": ["path", "subcommand"],
        },
    ),
    ToolDefinition(
        name="strata.list_checks",
        description="List all registered STRATA checkers with their descriptions and supported languages.",
        category=ToolCategory.INTROSPECTION,
        safety=ToolSafety.READ,
        input_schema={"type": "object", "properties": {}},
    ),
]
