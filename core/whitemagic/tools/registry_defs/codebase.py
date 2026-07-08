"""Registry definitions for codebase self-model tools.

These tools enable the agent to scan, recall, and navigate the codebase
via galactic/holographic memory — replacing raw grep with semantic recall.
"""

from __future__ import annotations

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="codebase.scan",
        description=(
            "Scan the codebase and ingest files + directory topology into the codex galaxy. "
            "Files are chunked with overlapping windows (no truncation data loss). "
            "Supports incremental mode (skips unchanged files via content-hash dedup). "
            "Optionally triggers semantic embedding indexing after ingestion. "
            "Use this to build a self-model of the project that enables semantic recall."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "project_root": {
                    "type": "string",
                    "description": "Root directory to scan. Defaults to WM_ROOT.",
                },
                "incremental": {
                    "type": "boolean",
                    "description": "If true, skip files whose content hash hasn't changed.",
                    "default": True,
                },
                "max_files": {
                    "type": "integer",
                    "description": "Maximum number of files to ingest.",
                    "default": 10000,
                },
                "embed": {
                    "type": "boolean",
                    "description": "If true, trigger semantic embedding indexing after ingestion.",
                    "default": True,
                },
            },
        },
    ),
    ToolDefinition(
        name="codebase.recall",
        description=(
            "Semantic recall from the codex galaxy. Searches file and chunk content "
            "memories using semantic embedding search, Rust BM25, or FTS5 fallback. "
            "Returns matching files with path, content preview, and recall type. "
            "This replaces grep for conceptual queries like 'where do we handle auth failures'."
        ),
        category=ToolCategory.MEMORY,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — natural language or keywords.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results.",
                    "default": 20,
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional tags to filter by.",
                },
                "min_importance": {
                    "type": "number",
                    "description": "Minimum importance score (0.0-1.0).",
                    "default": 0.0,
                },
                "semantic": {
                    "type": "boolean",
                    "description": "If true, use semantic embedding search when available.",
                    "default": True,
                },
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="codebase.structure",
        description=(
            "Recall directory topology from the codex galaxy. "
            "Returns files and subdirectories for a given path from stored memories. "
            "No filesystem access needed — reads from galactic memory."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path (e.g. 'core/whitemagic/tools'). Defaults to root.",
                },
            },
        },
    ),
    ToolDefinition(
        name="codebase.status",
        description=(
            "Get codebase scan status — last scan time, file counts, extension breakdown, "
            "chunk count, embedding count, and scan duration."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
    ToolDefinition(
        name="codebase.find",
        description=(
            "Find files by extension, tag, or path pattern in the codex galaxy. "
            "Faster than grep for 'what files exist with extension X' queries. "
            "Searches memory metadata, not the filesystem."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "extension": {
                    "type": "string",
                    "description": "File extension to filter by (e.g. 'py', 'rs').",
                },
                "path_pattern": {
                    "type": "string",
                    "description": "Path pattern to filter by (e.g. 'core/whitemagic').",
                },
                "tag": {
                    "type": "string",
                    "description": "Specific tag to filter by.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results.",
                    "default": 50,
                },
            },
        },
    ),
]
