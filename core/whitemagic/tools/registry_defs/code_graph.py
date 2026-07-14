"""Registry definitions for code structure graph tools.

These tools provide AST-level code graph operations: build, query,
path tracing, explain, community detection, and god node identification.
"""
from __future__ import annotations

from whitemagic.tools.tool_types import ToolCategory, ToolDefinition, ToolSafety

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="code.graph",
        description=(
            "Build or rebuild the code structure graph from source files. "
            "Extracts functions, classes, files, modules as nodes and "
            "calls, imports, inherits, defines as edges using tree-sitter (Rust) "
            "or Python ast/regex fallback. Supports incremental mode (only reparse "
            "changed files via content hash). Persists to SQLite for fast queries."
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
                    "description": "If true, only reparse files whose content hash changed.",
                    "default": True,
                },
                "max_files": {
                    "type": "integer",
                    "description": "Maximum number of files to process.",
                    "default": 50000,
                },
            },
        },
    ),
    ToolDefinition(
        name="code.query",
        description=(
            "Natural language query against the code structure graph. "
            "Supports patterns like 'what calls X', 'what does X call', "
            "'path from X to Y', 'explain X', 'communities', 'god nodes'. "
            "Returns matching nodes, edges, or analysis results."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results.",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="code.path",
        description=(
            "Trace the call path between two symbols (A → B) in the code graph. "
            "Uses BFS on the edge graph. Returns the path, hop count, and node names."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "symbol_a": {
                    "type": "string",
                    "description": "Starting symbol name.",
                },
                "symbol_b": {
                    "type": "string",
                    "description": "Target symbol name.",
                },
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum search depth.",
                    "default": 5,
                },
            },
            "required": ["symbol_a", "symbol_b"],
        },
    ),
    ToolDefinition(
        name="code.explain",
        description=(
            "Explain a symbol's role in the codebase: degree, incoming/outgoing "
            "edges, source location, language. Useful for understanding a function's "
            "connectivity and dependencies."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol name to explain.",
                },
            },
            "required": ["symbol"],
        },
    ),
    ToolDefinition(
        name="code.communities",
        description=(
            "Detect communities (subsystems) in the code structure graph. "
            "Uses Louvain community detection when networkx is available, "
            "falls back to connected components. Returns community sizes, "
            "member names, and associated files."
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
        name="code.god_nodes",
        description=(
            "List the most-connected symbols (highest degree centrality) in the "
            "code graph. These 'god nodes' are candidates for refactoring — "
            "they have too many dependencies."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results.",
                    "default": 10,
                },
            },
        },
    ),
    ToolDefinition(
        name="code.subgraph",
        description=(
            "Extract the neighborhood around a symbol up to a given depth. "
            "Returns all nodes and edges within the specified hop distance."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Center symbol name.",
                },
                "depth": {
                    "type": "integer",
                    "description": "Neighborhood depth (hop distance).",
                    "default": 2,
                },
            },
            "required": ["symbol"],
        },
    ),
    ToolDefinition(
        name="code.export",
        description=(
            "Export the code structure graph to Graphify-compatible graph.json format. "
            "Includes all nodes, edges, and metadata."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Output file path for graph.json.",
                },
            },
            "required": ["path"],
        },
    ),
    ToolDefinition(
        name="code.stats",
        description=(
            "Get code structure graph statistics: node count, edge count, "
            "node types, edge types, last build time, project root, "
            "and Rust availability."
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
        name="code.import",
        description=(
            "Import a Graphify-compatible graph.json file into the code structure graph. "
            "Supports the standard graph.json format with nodes and edges arrays. "
            "Useful for importing graphs built by Graphify or other compatible tools."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the graph.json file to import.",
                },
            },
            "required": ["path"],
        },
    ),
    ToolDefinition(
        name="code.affected_by",
        description=(
            "Find all symbols that would be affected if the given symbol changes. "
            "Performs reverse traversal of calls, imports, and references up to "
            "a configurable depth. Useful for impact analysis before refactoring."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Name of the symbol to analyze.",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum traversal depth (default 3).",
                    "default": 3,
                },
            },
            "required": ["symbol"],
        },
    ),
    ToolDefinition(
        name="code.correlate",
        description=(
            "Find memories that discuss a given code symbol. "
            "Searches for discussed_in edges and also performs semantic search "
            "on the codex galaxy for memories mentioning the symbol name."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Name of the code symbol to correlate with memories.",
                },
            },
            "required": ["symbol"],
        },
    ),
    ToolDefinition(
        name="code.cross_repo_query",
        description=(
            "Query across multiple repositories in a cross-repo graph. "
            "Requires repos to be added via cross-repo graph building first. "
            "Results include repo attribution for each match."
        ),
        category=ToolCategory.SYSTEM,
        safety=ToolSafety.READ,
        gana="gana_chariot",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query to search across repos.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default 20).",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    ),
]
