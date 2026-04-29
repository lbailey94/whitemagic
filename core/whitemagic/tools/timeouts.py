"""Centralized Tool Timeout Configuration

Consolidates all tool timeout budgets in one location.

Timeout Resolution Order (highest to lowest priority):
1. Tool-specific override in _TOOL_TIMEOUT_OVERRIDES
2. Timeout class mapping in _TOOL_TIMEOUT_CLASS_BY_TOOL
3. Class budget in _TOOL_TIMEOUT_CLASS_BUDGETS_S
4. Environment variable overrides
5. Default timeout (30.0s)

Usage:
    from whitemagic.tools.timeouts import get_timeout_for_tool
    timeout = get_timeout_for_tool("create_memory")
"""

import os
from typing import Any

# =============================================================================
# Base Configuration
# =============================================================================

_DEFAULT_TOOL_TIMEOUT_S = float(os.getenv("WM_TOOL_DISPATCH_TIMEOUT_S", "30.0"))

# =============================================================================
# Timeout Class Budgets
# =============================================================================

_TIMEOUT_CLASS_BUDGETS: dict[str, float] = {
    # Status/introspection tools (fast, read-only)
    "cold_status": float(os.getenv("WM_TOOL_TIMEOUT_COLD_STATUS_S", "15.0")),
    "introspection": 10.0,
    "health_check": 10.0,
    # Memory operations
    "memory_read": 15.0,
    "memory_write": 30.0,
    "memory_search": 20.0,
    "memory_consolidate": 60.0,  # Heavy operation
    # Generation/inference
    "local_generation": float(os.getenv("WM_TOOL_TIMEOUT_LOCAL_GENERATION_S", "30.0")),
    "agent_generation": float(os.getenv("WM_TOOL_TIMEOUT_AGENT_GENERATION_S", "45.0")),
    "remote_inference": 120.0,  # External API calls
    # File system operations
    "file_read": 30.0,
    "file_write": 45.0,
    "filesystem_scan": 90.0,  # File walks can be heavy
    # External operations
    "external_api": 60.0,
    "browser_automation": 120.0,
    "network_request": 45.0,
    # Data processing
    "batch_operation": 60.0,
    "data_export": 45.0,
    "data_import": 60.0,
    # Default fallback
    "default": _DEFAULT_TOOL_TIMEOUT_S,
}

# =============================================================================
# Tool-to-Timeout-Class Mapping
# =============================================================================

_TOOL_TIMEOUT_CLASS_BY_TOOL: dict[str, str] = {
    # Status/introspection (cold_status)
    "vector.status": "cold_status",
    "prompt.list": "cold_status",
    "forge.status": "cold_status",
    "capabilities": "introspection",
    "manifest": "introspection",
    "state.paths": "introspection",
    "state.summary": "introspection",
    "ship.check": "introspection",
    "health_report": "health_check",
    "gnosis": "health_check",

    # Memory operations
    "create_memory": "memory_write",
    "update_memory": "memory_write",
    "delete_memory": "memory_write",
    "search_memories": "memory_search",
    "read_memory": "memory_read",
    "batch_read_memories": "memory_read",
    "memory.consolidate": "memory_consolidate",

    # Ollama/local generation
    "ollama.generate": "local_generation",
    "ollama.chat": "local_generation",
    "ollama.models": "cold_status",
    "ollama.agent": "agent_generation",

    # File system operations
    "garden.list_files": "file_read",
    "garden.read_file": "file_read",
    "garden.write_file": "file_write",
    "grimoire_list": "filesystem_scan",
    "grimoire.read": "filesystem_scan",
    "archaeology.scan": "filesystem_scan",
    "fast_read_memory": "file_read",

    # External operations
    "browser_automation": "browser_automation",
    "browser_navigate": "browser_automation",
    "browser_click": "browser_automation",
    "browser_type": "browser_automation",
    "browser_extract_dom": "browser_automation",
    "web_research": "network_request",

    # Data operations
    "export_memories": "data_export",
    "import_memories": "data_import",
    "kg.export": "data_export",
    "kg.import": "data_import",

    # Batch operations
    "batch_create_memories": "batch_operation",
}

# =============================================================================
# Tool-Specific Timeout Overrides
# (Highest priority - use sparingly for edge cases)
# =============================================================================

_TOOL_TIMEOUT_OVERRIDES: dict[str, float] = {
    # Individual tool overrides for special cases
    # Format: "tool_name": timeout_seconds
}

# =============================================================================
# Tool Classification (Lightweight vs Heavyweight)
# =============================================================================

# Tools that are always fast and safe to call frequently
# These bypass normal dispatch and go through _dispatch_lightweight_tool()
# Only include tools that are handled in unified_api.py _dispatch_lightweight_tool()
LIGHTWEIGHT_STATUS_TOOLS: frozenset[str] = frozenset([
    "vector.status",
    "prompt.list",
    "forge.status",
])

# Fast interactive write tools (bypass some checks for responsiveness)
FAST_INTERACTIVE_WRITE_TOOLS: frozenset[str] = frozenset([
    "create_memory",
])

# Tools that should skip nervous system checks for performance
SKIP_NERVOUS_SYSTEM_CHECK: frozenset[str] = frozenset([
    "capabilities",
    "manifest",
    "state.paths",
    "state.summary",
    "repo.summary",
    "ship.check",
    "health_report",
    "gnosis",
    "get_telemetry_summary",
    "rust_status",
    "tool.graph",
    "tool.graph_full",
])

# =============================================================================
# Public API
# =============================================================================

def get_timeout_for_tool(tool_name: str) -> float:
    """Get the timeout (in seconds) for a specific tool.

    Resolution order:
    1. Tool-specific override
    2. Timeout class mapping
    3. Class budget
    4. Default

    Args:
        tool_name: The canonical tool name

    Returns:
        Timeout in seconds
    """
    # 1. Check for tool-specific override
    if tool_name in _TOOL_TIMEOUT_OVERRIDES:
        return _TOOL_TIMEOUT_OVERRIDES[tool_name]

    # 2. Get timeout class for tool
    timeout_class = _TOOL_TIMEOUT_CLASS_BY_TOOL.get(tool_name, "default")

    # 3. Get budget for class
    return _TIMEOUT_CLASS_BUDGETS.get(timeout_class, _DEFAULT_TOOL_TIMEOUT_S)


def get_timeout_class(tool_name: str) -> str:
    """Get the timeout class for a tool."""
    return _TOOL_TIMEOUT_CLASS_BY_TOOL.get(tool_name, "default")


def set_tool_timeout_override(tool_name: str, timeout: float) -> None:
    """Set a runtime timeout override for a specific tool.

    This is intended for testing and emergency tuning.
    Permanent changes should be made in this config file.
    """
    _TOOL_TIMEOUT_OVERRIDES[tool_name] = timeout


def is_lightweight_tool(tool_name: str) -> bool:
    """Check if a tool is classified as lightweight."""
    return tool_name in LIGHTWEIGHT_STATUS_TOOLS


def is_fast_interactive_write(tool_name: str) -> bool:
    """Check if a tool is a fast interactive write operation."""
    return tool_name in FAST_INTERACTIVE_WRITE_TOOLS


def should_skip_nervous_system_check(tool_name: str) -> bool:
    """Check if a tool should bypass nervous system checks."""
    return tool_name in SKIP_NERVOUS_SYSTEM_CHECK


def get_all_timeout_config() -> dict[str, Any]:
    """Get complete timeout configuration for debugging/export."""
    return {
        "default_timeout": _DEFAULT_TOOL_TIMEOUT_S,
        "class_budgets": _TIMEOUT_CLASS_BUDGETS.copy(),
        "tool_class_mappings": _TOOL_TIMEOUT_CLASS_BY_TOOL.copy(),
        "overrides": _TOOL_TIMEOUT_OVERRIDES.copy(),
        "lightweight_tools": list(LIGHTWEIGHT_STATUS_TOOLS),
        "fast_write_tools": list(FAST_INTERACTIVE_WRITE_TOOLS),
        "skip_nervous_check": list(SKIP_NERVOUS_SYSTEM_CHECK),
    }
