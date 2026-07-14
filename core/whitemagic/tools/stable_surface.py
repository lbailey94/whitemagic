"""Canonical stable tool surface for WhiteMagic's first public release.

This module defines the authoritative set of tools that constitute the
supported public API.  Only tools listed here are:
- Shown in default MCP tool listings
- Guaranteed to maintain backward compatibility
- Covered by the release gate smoke tests

Every other tool is either OPTIONAL (exists but not guaranteed stable) or
EXPERIMENTAL (may change or disappear without notice).

The stability of a tool is determined by ``ToolDefinition.stability``, which
is the single source of truth.  The legacy ``stable_contract.py`` module is
deprecated in favour of this module.
"""

from __future__ import annotations

# ── Core memory CRUD ────────────────────────────────────────────────
_MEMORY_TOOLS: frozenset[str] = frozenset({
    "create_memory",
    "update_memory",
    "delete_memory",
    "search_memories",
    "hybrid_recall",
    "memory_read",
})

# ── Unified read/write (already STABLE in registry_defs) ────────────
_UNIFIED_TOOLS: frozenset[str] = frozenset({
    "wm_read",
    "wm_write",
    "wm_read.status",
    "wm_write.status",
    "wm",
})

# ── Session and state ───────────────────────────────────────────────
_SESSION_TOOLS: frozenset[str] = frozenset({
    "state.current",
    "session.record",
    "session.recall",
    "session.continuity",
})

# ── Introspection ───────────────────────────────────────────────────
_INTROSPECTION_TOOLS: frozenset[str] = frozenset({
    "gnosis",
    "capabilities",
    "manifest",
    "health_report",
})

# ── Galaxy management (read-only) ───────────────────────────────────
_GALAXY_TOOLS: frozenset[str] = frozenset({
    "galaxy.list",
    "galaxy.stats",
    "galaxy.status",
})

# ── Governance ──────────────────────────────────────────────────────
_GOVERNANCE_TOOLS: frozenset[str] = frozenset({
    "governor_validate",
    "karmic.effects",
    "karmic.debt",
})

# ── Consciousness status (fast-path, read-only) ─────────────────────
_CONSCIOUSNESS_TOOLS: frozenset[str] = frozenset({
    "consciousness.loop.status",
    "guna.balance.status",
    "meta.galaxy.overview",
    "galactic.dashboard",
})

# ── All 28 Gana meta-tools (set STABLE in tool_catalog.py) ──────────
# This is validated dynamically — any gana_* tool is STABLE.

# ── Complete stable surface ─────────────────────────────────────────
STABLE_TOOL_NAMES: frozenset[str] = (
    _MEMORY_TOOLS
    | _UNIFIED_TOOLS
    | _SESSION_TOOLS
    | _INTROSPECTION_TOOLS
    | _GALAXY_TOOLS
    | _GOVERNANCE_TOOLS
    | _CONSCIOUSNESS_TOOLS
)


def is_stable(tool_name: str) -> bool:
    """Check if a tool is part of the stable public surface.

    Gana meta-tools (gana_*) are always stable.
    """
    if tool_name.startswith("gana_"):
        return True
    return tool_name in STABLE_TOOL_NAMES


def get_stable_tool_names() -> frozenset[str]:
    """Return the complete set of stable tool names (including gana_*)."""
    from whitemagic.tools.registry import get_all_tools

    gana_names = {t.name for t in get_all_tools() if t.name.startswith("gana_")}
    return STABLE_TOOL_NAMES | frozenset(gana_names)
