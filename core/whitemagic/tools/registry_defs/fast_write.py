"""Fast Write Tools — Atomic file writing with syntax validation.

Provides safe, fast file writing via MCP with built-in syntax checking.
Registered under Chariot (codebase navigation) in the PRAT system.
"""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="fast_write.write",
        description="Write content to a file atomically with syntax validation. Overwrites if file exists. 10-100x faster than edit tools for >10 line changes.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target file path"},
                "content": {"type": "string", "description": "File content to write"},
                "validate": {"type": "boolean", "default": True, "description": "Validate Python syntax after write"},
                "backup": {"type": "boolean", "default": False, "description": "Backup existing file to .bak before write"},
                "dry_run": {"type": "boolean", "default": False, "description": "Show what would be written without writing"},
            },
            "required": ["path", "content"],
        },
    ),
    ToolDefinition(
        name="fast_write.append",
        description="Append content to an existing file with optional syntax validation.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target file path"},
                "content": {"type": "string", "description": "Content to append"},
                "validate": {"type": "boolean", "default": True, "description": "Validate Python syntax after append"},
            },
            "required": ["path", "content"],
        },
    ),
    ToolDefinition(
        name="fast_write.batch",
        description="Write multiple files in one operation with syntax validation.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "files": {"type": "object", "description": "Dict of {path: content} pairs"},
                "validate": {"type": "boolean", "default": True},
                "backup": {"type": "boolean", "default": False},
            },
            "required": ["files"],
        },
    ),
    ToolDefinition(
        name="fast_write.validate",
        description="Validate syntax of a file without writing. Checks Python (ast.parse) or basic encoding for other types.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to validate"},
            },
            "required": ["path"],
        },
    ),
]
