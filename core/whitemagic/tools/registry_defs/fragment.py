"""Fragment Tools — Rust-accelerated codebase indexing and search.

Fragment provides 100x faster BM25+semantic search via PyO3, HTTP, or subprocess layers.
Registered under Winnowing Basket (search) in the PRAT system.
"""

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="fragment.search",
        description="Search a codebase index for relevant code chunks using Fragment (Rust). 100x faster than Python vector search with BM25+semantic scoring.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "path": {"type": "string", "description": "Path to the codebase root directory"},
                "top": {"type": "integer", "description": "Number of results to return", "default": 10},
                "index_dir": {"type": "string", "description": "Custom index directory path (default: <path>/.fragment)"},
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="fragment.index",
        description="Build or update a Fragment index for a codebase. Supports quick (BM25 only) and deep (hybrid+semantic) modes.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the codebase to index"},
                "mode": {"type": "string", "enum": ["quick", "deep"], "default": "quick"},
                "force": {"type": "boolean", "default": False, "description": "Force rebuild from scratch"},
            },
            "required": ["path"],
        },
    ),
    ToolDefinition(
        name="fragment.status",
        description="Show Fragment index statistics for a project — file count, chunk count, index size, build mode.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the codebase"},
                "index_dir": {"type": "string", "description": "Custom index directory path"},
            },
            "required": ["path"],
        },
    ),
    ToolDefinition(
        name="fragment.query",
        description="Alias for fragment.search — query a Fragment index for relevant code chunks.",
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "path": {"type": "string", "description": "Path to the codebase"},
                "top": {"type": "integer", "default": 10},
            },
            "required": ["query", "path"],
        },
    ),
]
