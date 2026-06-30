# ruff: noqa: BLE001
"""Registry definitions for wiki and external repo tools."""

from typing import Any


def get_wiki_tool_defs() -> list[dict[str, Any]]:
    """Return tool definitions for the internal wiki suite."""
    return [
        {
            "name": "wiki.generate",
            "description": (
                "Generate or refresh internal wiki entries from codebase analysis. "
                "Scans Python modules, tool registry, PRAT Ganas, and pattern library. "
                "Categories: architecture, module, pattern, antipattern, api, guide."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["all", "modules", "tools", "patterns", "ganas"],
                        "default": "all",
                        "description": "What to scan",
                    },
                    "root": {
                        "type": "string",
                        "description": "Root directory (defaults to PROJECT_ROOT)",
                    },
                    "force": {
                        "type": "boolean",
                        "default": False,
                        "description": "Overwrite existing entries",
                    },
                },
            },
            "category": "codebase",
            "safety": "read",
        },
        {
            "name": "wiki.query",
            "description": (
                "Query the internal wiki by text search, category, or tags. "
                "Returns matching entries with content previews."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text search"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "architecture",
                            "module",
                            "pattern",
                            "antipattern",
                            "api",
                            "guide",
                        ],
                    },
                    "tags": {"type": "string", "description": "Comma-separated tags"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
            "category": "codebase",
            "safety": "read",
        },
        {
            "name": "wiki.update",
            "description": (
                "Update a specific wiki entry by id or title. "
                "Requires content; category defaults to 'guide'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Entry ID"},
                    "title": {"type": "string", "description": "Entry title"},
                    "content": {"type": "string", "description": "New content"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "architecture",
                            "module",
                            "pattern",
                            "antipattern",
                            "api",
                            "guide",
                        ],
                        "default": "guide",
                    },
                    "tags": {"type": "string", "description": "Comma-separated"},
                },
                "required": ["content"],
            },
            "category": "codebase",
            "safety": "write",
        },
        {
            "name": "wiki.scan",
            "description": (
                "Scan for documentation drift — detects wiki entries whose "
                "source files have been modified after the entry was last updated."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "root": {"type": "string", "description": "Root directory"},
                },
            },
            "category": "codebase",
            "safety": "read",
        },
        {
            "name": "wiki.stats",
            "description": "Get internal wiki statistics (entry counts by category, avg confidence).",
            "parameters": {"type": "object", "properties": {}},
            "category": "codebase",
            "safety": "read",
        },
    ]


def get_external_repo_tool_defs() -> list[dict[str, Any]]:
    """Return tool definitions for external repository tools."""
    return [
        {
            "name": "external.wiki_query",
            "description": (
                "Query an external GitHub repository's wiki via DeepWiki MCP. "
                "When DeepWiki is configured in the MCP host, this routes to "
                "the ask_question tool. Otherwise returns guidance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "GitHub repo in owner/repo format",
                    },
                    "question": {
                        "type": "string",
                        "description": "Natural language question",
                    },
                },
                "required": ["repo", "question"],
            },
            "category": "codebase",
            "safety": "read",
        },
        {
            "name": "external.repo_scan",
            "description": (
                "Clone and scan an external repository using archaeology tools. "
                "Shallow clones, extracts module structure, docstrings, and patterns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "owner/repo format or full URL",
                    },
                    "depth": {"type": "integer", "default": 3},
                    "cleanup": {"type": "boolean", "default": True},
                },
                "required": ["repo"],
            },
            "category": "codebase",
            "safety": "read",
        },
        {
            "name": "external.repo_compare",
            "description": (
                "Compare a local module with an external repository's structure. "
                "Useful for understanding how other projects solve similar problems."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "owner/repo"},
                    "local_module": {"type": "string", "description": "Local path"},
                },
                "required": ["repo", "local_module"],
            },
            "category": "codebase",
            "safety": "read",
        },
    ]
