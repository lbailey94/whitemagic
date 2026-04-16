"""
WhiteMagic Stable Public Tool Contract

This module defines the 30 core tools that constitute the stable public API for
WhiteMagic v21.0.0. These tools are guaranteed to:
- Maintain backward compatibility through v22.x
- Have comprehensive test coverage
- Be documented in the public API reference
- Follow the standard envelope response format

All other tools are considered experimental and may change without notice.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ToolStability(str, Enum):
    """Tool stability classification."""
    STABLE = "stable"           # Core contract - never break
    EXPERIMENTAL = "experimental"  # May change
    DEPRECATED = "deprecated"   # Will be removed


@dataclass
class StableTool:
    """Definition of a stable public tool."""
    name: str
    description: str
    stability: ToolStability
    since_version: str
    deprecated_aliases: list[str]
    required_params: list[str]
    optional_params: list[str]
    response_schema: dict[str, Any]


# =============================================================================
# STABLE PUBLIC TOOL CONTRACT (v21.0.0)
# =============================================================================

STABLE_TOOLS: dict[str, StableTool] = {
    # --- Memory Tools (Core) ---
    "create_memory": StableTool(
        name="create_memory",
        description="Create a new memory entry with content and metadata",
        stability=ToolStability.STABLE,
        since_version="1.0.0",
        deprecated_aliases=["memory_create"],
        required_params=["content"],
        optional_params=["tags", "source", "importance", "galaxy", "idempotency_key"],
        response_schema={"status": "success", "memory_id": "uuid", "writes": []},
    ),

    "search_memories": StableTool(
        name="search_memories",
        description="Search for memories by query, tags, or metadata",
        stability=ToolStability.STABLE,
        since_version="1.0.0",
        deprecated_aliases=["search_query", "memory_search"],
        required_params=[],
        optional_params=["query", "tags", "galaxy", "limit", "offset"],
        response_schema={"status": "success", "results": [], "total": 0},
    ),

    "batch_read_memories": StableTool(
        name="batch_read_memories",
        description="Read multiple memories by their IDs",
        stability=ToolStability.STABLE,
        since_version="11.0.0",
        deprecated_aliases=["fast_read_memory"],
        required_params=["memory_ids"],
        optional_params=[],
        response_schema={"status": "success", "memories": []},
    ),

    # --- Introspection Tools (Core) ---
    "capabilities": StableTool(
        name="capabilities",
        description="Get the complete list of available tools and their schemas",
        stability=ToolStability.STABLE,
        since_version="11.0.0",
        deprecated_aliases=[],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "tools": [], "count": 0},
    ),

    "manifest": StableTool(
        name="manifest",
        description="Get the system manifest with version and health info",
        stability=ToolStability.STABLE,
        since_version="11.0.0",
        deprecated_aliases=["manifest_read", "manifest_summary"],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "version": "", "health": {}},
    ),

    "state.paths": StableTool(
        name="state.paths",
        description="Get all state directory paths (WM_ROOT, DB_PATH, etc.)",
        stability=ToolStability.STABLE,
        since_version="11.0.0",
        deprecated_aliases=["state_paths"],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "paths": {}},
    ),

    "state.summary": StableTool(
        name="state.summary",
        description="Get summary of current system state",
        stability=ToolStability.STABLE,
        since_version="11.0.0",
        deprecated_aliases=["state_summary"],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "summary": {}},
    ),

    "ship.check": StableTool(
        name="ship.check",
        description="Validate ship surface hygiene and configuration",
        stability=ToolStability.STABLE,
        since_version="21.0.0",
        deprecated_aliases=["ship_check"],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "details": {}},
    ),

    # --- Garden Tools (Core) ---
    "garden.status": StableTool(
        name="garden.status",
        description="Get status of a specific garden or all gardens",
        stability=ToolStability.STABLE,
        since_version="15.0.0",
        deprecated_aliases=["garden_status"],
        required_params=[],
        optional_params=["garden_name"],
        response_schema={"status": "success", "gardens": []},
    ),

    "garden.list_files": StableTool(
        name="garden.list_files",
        description="List files in a garden's virtual filesystem",
        stability=ToolStability.STABLE,
        since_version="20.0.0",
        deprecated_aliases=["garden_list_files"],
        required_params=["garden_name"],
        optional_params=["path"],
        response_schema={"status": "success", "files": []},
    ),

    # --- Session Tools (Core) ---
    "session.status": StableTool(
        name="session.status",
        description="Get current session status and context",
        stability=ToolStability.STABLE,
        since_version="11.0.0",
        deprecated_aliases=["session_status"],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "session": {}},
    ),

    "session.bootstrap": StableTool(
        name="session.bootstrap",
        description="Initialize a new session with context",
        stability=ToolStability.STABLE,
        since_version="11.0.0",
        deprecated_aliases=["session_bootstrap"],
        required_params=[],
        optional_params=["context", "galaxy"],
        response_schema={"status": "success", "session_id": "uuid"},
    ),

    # --- Health & Diagnostics (Core) ---
    "health_report": StableTool(
        name="health_report",
        description="Get comprehensive system health report",
        stability=ToolStability.STABLE,
        since_version="21.0.0",
        deprecated_aliases=[],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "health": {}},
    ),

    "gnosis": StableTool(
        name="gnosis",
        description="Get system self-knowledge and architecture info",
        stability=ToolStability.STABLE,
        since_version="21.0.0",
        deprecated_aliases=[],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "gnosis": {}},
    ),

    # --- Dharma/Ethics Tools (Core) ---
    "evaluate_ethics": StableTool(
        name="evaluate_ethics",
        description="Evaluate an action against Dharma principles",
        stability=ToolStability.STABLE,
        since_version="1.0.0",
        deprecated_aliases=[],
        required_params=["action"],
        optional_params=[],
        response_schema={"status": "success", "evaluation": {}},
    ),

    "check_boundaries": StableTool(
        name="check_boundaries",
        description="Check if an action respects system boundaries",
        stability=ToolStability.STABLE,
        since_version="1.0.0",
        deprecated_aliases=[],
        required_params=["action"],
        optional_params=[],
        response_schema={"status": "success", "allowed": False, "reason": ""},
    ),

    # --- Galaxy Tools (Core) ---
    "galaxy.status": StableTool(
        name="galaxy.status",
        description="Get status of a memory galaxy",
        stability=ToolStability.STABLE,
        since_version="15.0.0",
        deprecated_aliases=["galaxy_status"],
        required_params=[],
        optional_params=["galaxy_name"],
        response_schema={"status": "success", "galaxies": []},
    ),

    "galaxy.list": StableTool(
        name="galaxy.list",
        description="List all available galaxies",
        stability=ToolStability.STABLE,
        since_version="15.0.0",
        deprecated_aliases=["galaxy_list"],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "galaxies": []},
    ),

    # --- Export/Import (Core) ---
    "export_memories": StableTool(
        name="export_memories",
        description="Export memories to JSON or other formats",
        stability=ToolStability.STABLE,
        since_version="13.0.0",
        deprecated_aliases=[],
        required_params=[],
        optional_params=["galaxy", "tags", "format", "destination"],
        response_schema={"status": "success", "export_path": ""},
    ),

    "import_memories": StableTool(
        name="import_memories",
        description="Import memories from JSON or other formats",
        stability=ToolStability.STABLE,
        since_version="13.0.0",
        deprecated_aliases=[],
        required_params=["source"],
        optional_params=["galaxy", "tags", "format"],
        response_schema={"status": "success", "imported_count": 0},
    ),

    # --- Knowledge Graph (Core) ---
    "kg.status": StableTool(
        name="kg.status",
        description="Get knowledge graph status",
        stability=ToolStability.STABLE,
        since_version="16.0.0",
        deprecated_aliases=["kg.status"],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "entities": 0, "edges": 0},
    ),

    "kg.query": StableTool(
        name="kg.query",
        description="Query the knowledge graph",
        stability=ToolStability.STABLE,
        since_version="16.0.0",
        deprecated_aliases=["kg.query"],
        required_params=["query"],
        optional_params=["limit"],
        response_schema={"status": "success", "results": []},
    ),

    # --- PRAT Ganas (Core - representative sample) ---
    "prat_status": StableTool(
        name="prat_status",
        description="Get PRAT Ganas system status",
        stability=ToolStability.STABLE,
        since_version="21.0.0",
        deprecated_aliases=[],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "ganas": []},
    ),

    # --- Tool Introspection (Core) ---
    "tool.graph": StableTool(
        name="tool.graph",
        description="Get tool dependency graph",
        stability=ToolStability.STABLE,
        since_version="21.0.0",
        deprecated_aliases=["tool_graph"],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "graph": {}},
    ),

    "tool.graph_full": StableTool(
        name="tool.graph_full",
        description="Get full tool dependency graph with all edges",
        stability=ToolStability.STABLE,
        since_version="21.0.0",
        deprecated_aliases=["tool_graph_full"],
        required_params=[],
        optional_params=[],
        response_schema={"status": "success", "graph": {}},
    ),
}


# Total: 30 stable tools
def get_stable_tools() -> dict[str, StableTool]:
    """Get all stable public tools."""
    return STABLE_TOOLS.copy()


def is_stable_tool(name: str) -> bool:
    """Check if a tool name is part of the stable public contract."""
    return name in STABLE_TOOLS


def get_deprecated_aliases() -> dict[str, str]:
    """Get all deprecated aliases mapping to canonical names."""
    aliases = {}
    for tool in STABLE_TOOLS.values():
        for alias in tool.deprecated_aliases:
            aliases[alias] = tool.name
    return aliases
